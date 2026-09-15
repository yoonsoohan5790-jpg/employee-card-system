"""
대량 테스트(더미) 데이터 생성 스크립트 - 임시/데모용.

사용법:
    python generate_bulk_test_data.py           # 800명 추가 생성
    python generate_bulk_test_data.py 300       # 원하는 인원수 지정

기존 조직원(admin, seed.py의 기본 5명 등)은 그대로 두고 무작위 조직원을 추가로 생성한다.
사원증 발급/출입권한 적용/중지 로직을 seed.py와 동일하게 그대로 통과시키므로,
audit_logs(변경 이력)도 실제 흐름과 똑같이 함께 쌓인다.

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
from services import card_service, access_service

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
    """
    start_idx = User.query.count()

    for i in range(count):
        dept, positions = random.choice(DEPT_POSITIONS)
        position = random.choice(positions)
        status = random_status()
        seq = start_idx + i + 1
        username = f"emp{seq:04d}"
        name = random_name()
        hire_date = date.today() - timedelta(days=random.randint(30, 365 * 8))

        user = User(
            username=username,
            name=name,
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

        db.session.add(user)
        db.session.flush()

        # seed.py와 동일한 발급/권한 흐름을 그대로 태워서 실제와 같은 변경 이력을 남긴다.
        if status == EMPLOYMENT_STATUS_ACTIVE:
            card_service.issue_card(user, actor="SYSTEM")
        else:
            access_service.apply_policy_for_user(user, actor="SYSTEM")
            card_service.issue_card(user, actor="SYSTEM")
            card_service.suspend_card(user, actor="SYSTEM", reason=f"{status} 처리")

        if (i + 1) % 100 == 0:
            db.session.commit()

    db.session.commit()
    total = User.query.count()
    from models.audit_log import AuditLog
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
