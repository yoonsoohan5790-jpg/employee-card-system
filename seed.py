"""
초기 테스트 데이터 생성 스크립트. (스펙 28조)
사용법: python seed.py
"""
from datetime import date, timedelta

from app import create_app
from extensions import db
from models.user import User, ROLE_ADMIN, ROLE_EMPLOYEE
from models.access_area import AccessArea
from models.access_policy import AccessPolicy
from services import card_service, access_service

AREAS = [
    ("AREA-01", "일반 사무구역", "전 직원 공용 사무 공간"),
    ("AREA-02", "회의실", "회의 및 협업 공간"),
    ("AREA-03", "서버실", "전산 장비 보관 구역"),
    ("AREA-04", "정보보호실", "보안 통제 구역"),
    ("AREA-05", "임원실", "임원 전용 구역"),
    ("AREA-06", "자료보관실", "기밀 자료 보관 구역"),
]

# (부서, 직급): {area_code: allowed}
POLICIES = {
    ("경영지원팀", "사원"): {"AREA-01": True, "AREA-02": True},
    ("경영지원팀", "팀장"): {"AREA-01": True, "AREA-02": True},
    ("IT팀", "사원"): {"AREA-01": True, "AREA-02": True, "AREA-03": True},
    ("IT팀", "과장"): {"AREA-01": True, "AREA-02": True, "AREA-03": True},
    ("정보보호팀", "사원"): {"AREA-01": True, "AREA-02": True, "AREA-03": True, "AREA-04": True},
    ("정보보호팀", "대리"): {"AREA-01": True, "AREA-02": True, "AREA-03": True, "AREA-04": True},
    ("영업팀", "과장"): {"AREA-01": True, "AREA-02": True},
    ("개발팀", "사원"): {"AREA-01": True, "AREA-02": True, "AREA-03": True},
    ("임원", "임원"): {"AREA-01": True, "AREA-02": True, "AREA-03": True, "AREA-04": True, "AREA-05": True, "AREA-06": True},
}

EMPLOYEES = [
    dict(username="hong", password="pass1234", name="홍길동", department="경영지원팀", position="사원",
         email="hong@etners.com", phone="010-1111-1111", hire_date=date(2023, 3, 2),
         employment_status="재직"),
    dict(username="kim", password="pass1234", name="김철수", department="IT팀", position="사원",
         email="kim@etners.com", phone="010-2222-2222", hire_date=date(2022, 7, 15),
         employment_status="재직"),
    dict(username="lee", password="pass1234", name="이영희", department="정보보호팀", position="대리",
         email="lee@etners.com", phone="010-3333-3333", hire_date=date(2021, 1, 11),
         employment_status="재직"),
    dict(username="park", password="pass1234", name="박민수", department="영업팀", position="과장",
         email="park@etners.com", phone="010-4444-4444", hire_date=date(2019, 5, 20),
         employment_status="휴직",
         leave_start_date=date.today() - timedelta(days=10),
         leave_end_date=date.today() + timedelta(days=80)),
    dict(username="choi", password="pass1234", name="최지훈", department="개발팀", position="사원",
         email="choi@etners.com", phone="010-5555-5555", hire_date=date(2020, 9, 1),
         employment_status="퇴사",
         resign_date=date.today() - timedelta(days=5)),
]


def run():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        area_map = {}
        for code, name, desc in AREAS:
            area = AccessArea(area_code=code, area_name=name, description=desc, active=True)
            db.session.add(area)
            db.session.flush()
            area_map[code] = area

        for (dept, pos), allowed_map in POLICIES.items():
            for code, allowed in allowed_map.items():
                db.session.add(AccessPolicy(department=dept, position=pos, area_id=area_map[code].id, allowed=allowed))
        db.session.flush()

        admin = User(username="admin", name="관리자", department="경영지원팀", position="관리자",
                     email="admin@etners.com", role=ROLE_ADMIN, employment_status="재직", hire_date=date.today())
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.flush()

        for emp in EMPLOYEES:
            data = dict(emp)
            password = data.pop("password")
            user = User(role=ROLE_EMPLOYEE, **data)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if user.employment_status == "재직":
                card_service.issue_card(user, actor="SYSTEM")
            else:
                access_service.apply_policy_for_user(user, actor="SYSTEM")
                if user.employment_status in ("휴직", "퇴사"):
                    card_service.issue_card(user, actor="SYSTEM")
                    card_service.suspend_card(user, actor="SYSTEM", reason=f"{user.employment_status} 처리")

        db.session.commit()
        print("초기 데이터 생성 완료.")
        print("관리자 계정: admin / admin123")
        print("조직원 계정 예시: hong / pass1234 (경영지원팀 사원)")


if __name__ == "__main__":
    run()
