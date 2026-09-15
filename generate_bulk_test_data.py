"""
대량 테스트(더미) 데이터 생성 스크립트 - 임시/데모용.

사용법:
    python generate_bulk_test_data.py           # 800명 추가 생성
    python generate_bulk_test_data.py 300       # 원하는 인원수 지정

기존 조직원(admin, seed.py의 기본 5명 등)은 그대로 두고 무작위 조직원을 추가로 생성한다.
정책/구역을 한 번만 조회한 뒤 사원증/출입권한/변경이력을 일괄(batch) insert하는 방식이라
원격 DB(Supabase 등) 대상으로도 800명 정도는 몇 초 내에 끝난다.

초기 데모 상태로 되돌리고 싶으면 `python seed.py`를 다시 실행한다 (전체 초기화 후 재시딩).
"""
import random
import sys
from datetime import date, timedelta

from extensions import db
from models.user import (
    User,
    ROLE_EMPLOYEE,
    EMPLOYMENT_STATUS_ACTIVE,
    EMPLOYMENT_STATUS_LEAVE,
    EMPLOYMENT_STATUS_RESIGNED,
)
from models.card import Card, CARD_STATUS_ACTIVE, CARD_STATUS_SUSPENDED
from models.access_area import AccessArea
from models.access_policy import AccessPolicy
from models.user_access import UserAccess, SOURCE_POLICY
from models.audit_log import AuditLog

SURNAMES = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오", "서", "신", "권", "황", "안", "송", "전", "홍"]
GIVEN = [
    "민준", "서연", "도윤", "서준", "하윤", "시우", "지우", "지호", "주원", "수아",
    "은우", "지안", "예준", "다은", "우진", "윤서", "현우", "소율", "건우", "나윤",
    "동현", "유진", "성민", "가은", "태윤", "채원", "시윤", "아린", "준서", "하은",
]

# 정책이 이미 설정된 부서/직급 위주 + 정책 없는 부서 하나(인사팀)를 섞어서
# "정책 미설정 -> 전부 차단"인 사례도 자연스럽게 만든다.
DEPT_POSITIONS = [
    ("경영지원팀", ["사원", "팀장"]),
    ("IT팀", ["사원", "과장"]),
    ("정보보호팀", ["사원", "대리"]),
    ("영업팀", ["사원", "과장"]),
    ("개발팀", ["사원", "대리", "과장"]),
    ("인사팀", ["사원", "대리"]),
]

STATUS_WEIGHTS = [
    (EMPLOYMENT_STATUS_ACTIVE, 0.85),
    (EMPLOYMENT_STATUS_LEAVE, 0.08),
    (EMPLOYMENT_STATUS_RESIGNED, 0.07),
]


def random_name():
    return random.choice(SURNAMES) + random.choice(GIVEN)


def random_status():
    r = random.random()
    cum = 0.0
    for status, weight in STATUS_WEIGHTS:
        cum += weight
        if r <= cum:
            return status
    return EMPLOYMENT_STATUS_ACTIVE


def generate(count=800):
    """
    현재 앱 컨텍스트의 DB에 무작위 조직원을 count명 추가한다.
    app.app_context()가 이미 열려 있다고 가정한다 (CLI에서든, 웹 요청 핸들러에서든).

    card_service/access_service를 사용자 1명당 개별 호출하면 사용자마다 여러 번의
    DB 왕복(쿼리)이 발생해, 네트워크 지연이 있는 원격 DB(Supabase 등)에서는
    800명 기준 수십 분이 걸려 서버리스 함수 제한 시간을 넘기기 쉽다.
    그래서 이 벌크 생성 전용 경로는 정책/구역을 한 번만 조회해두고
    User/Card/UserAccess/AuditLog를 모아서 일괄 insert하는 방식으로 처리한다.
    (개별 사원증 발급/예외처리 등 실사용 흐름은 여전히 card_service/access_service를 사용한다.)
    """
    start_idx = User.query.count()

    policy_map_by_dept_position = {}
    for row in AccessPolicy.query.all():
        policy_map_by_dept_position.setdefault((row.department, row.position), {})[row.area_id] = row.allowed
    areas = AccessArea.query.filter_by(active=True).all()

    year = date.today().year
    last_card = (
        Card.query.filter(Card.card_id.like(f"CARD-{year}-%"))
        .order_by(Card.card_id.desc())
        .first()
    )
    next_seq = int(last_card.card_id.split("-")[-1]) + 1 if last_card else 1

    user_objs = []
    for i in range(count):
        dept, positions = random.choice(DEPT_POSITIONS)
        position = random.choice(positions)
        status = random_status()
        seq = start_idx + i + 1
        username = f"emp{seq:04d}"
        hire_date = date.today() - timedelta(days=random.randint(30, 365 * 8))

        user = User(
            username=username,
            name=random_name(),
            department=dept,
            position=position,
            email=f"{username}@etners.com",
            phone=f"010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            hire_date=hire_date,
            employment_status=status,
            role=ROLE_EMPLOYEE,
        )
        user.set_password("test1234")

        if status == EMPLOYMENT_STATUS_LEAVE:
            user.leave_start_date = date.today() - timedelta(days=random.randint(1, 60))
            user.leave_end_date = date.today() + timedelta(days=random.randint(10, 120))
        elif status == EMPLOYMENT_STATUS_RESIGNED:
            user.resign_date = date.today() - timedelta(days=random.randint(1, 200))

        user_objs.append(user)

    db.session.add_all(user_objs)
    db.session.flush()  # user.id를 한 번의 배치 insert로 확보

    card_objs = []
    access_objs = []
    audit_objs = []
    seq_counter = next_seq

    for user in user_objs:
        card_id = f"CARD-{year}-{seq_counter:06d}"
        seq_counter += 1
        is_active = user.employment_status == EMPLOYMENT_STATUS_ACTIVE
        card_objs.append(Card(
            card_id=card_id,
            user_id=user.id,
            issue_date=date.today(),
            status=CARD_STATUS_ACTIVE if is_active else CARD_STATUS_SUSPENDED,
        ))

        policy_map = policy_map_by_dept_position.get((user.department, user.position), {})
        for area in areas:
            allowed = is_active and bool(policy_map.get(area.id, False))
            access_objs.append(UserAccess(user_id=user.id, area_id=area.id, allowed=allowed, source=SOURCE_POLICY))

        action = "사원증 발급 (대량 생성)" if is_active else f"사원증 발급 후 중지 (대량 생성, {user.employment_status})"
        audit_objs.append(AuditLog(user_id=user.id, card_id=card_id, action=action, actor="SYSTEM"))

    db.session.add_all(card_objs)
    db.session.add_all(access_objs)
    db.session.add_all(audit_objs)
    db.session.commit()

    total = User.query.count()
    log_count = AuditLog.query.count()
    return {"added": count, "total_users": total, "audit_logs": log_count}


def run(count=800):
    """로컬 CLI 진입점: 직접 app context를 만들어 generate()를 호출한다."""
    from app import create_app

    app = create_app()
    with app.app_context():
        print(f"{count}명 추가 생성 시작...")
        result = generate(count)
        print(f"완료. 전체 조직원 {result['total_users']}명, 누적 변경 이력(audit_logs) {result['audit_logs']}건")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    run(n)
