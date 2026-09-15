"""
일반 사용자의 사원증 신청 처리.

- 기타사항(note)이 없으면 즉시 자동 승인: 계정 생성 + 사원증 자동 발급.
- 기타사항이 있으면 '검토 대기'로 등록하고 관리자 승인/반려를 거친다.
"""
from datetime import date

from extensions import db
from models.card_application import CardApplication, STATUS_APPROVED, STATUS_PENDING, STATUS_REJECTED
from models.user import User, ROLE_EMPLOYEE, EMPLOYMENT_STATUS_ACTIVE
from models.audit_log import AuditLog, ACTOR_SYSTEM
from services import card_service

DEFAULT_TEMP_PASSWORD = "changeme123"


class ApplicationError(Exception):
    """신청 제출/처리 중 사용자에게 그대로 보여줄 수 있는 오류."""


def _create_user_from_application(app_row, actor):
    if User.query.filter_by(username=app_row.employee_number).first():
        raise ApplicationError(f"사번 '{app_row.employee_number}'은(는) 이미 등록되어 있습니다.")

    user = User(
        username=app_row.employee_number,
        name=app_row.name,
        department=app_row.department,
        position=app_row.position,
        employment_status=EMPLOYMENT_STATUS_ACTIVE,
        role=ROLE_EMPLOYEE,
        hire_date=date.today(),
    )
    user.set_password(DEFAULT_TEMP_PASSWORD)
    db.session.add(user)
    db.session.flush()

    card_service.issue_card(user, actor=actor)

    log = AuditLog(
        user_id=user.id,
        card_id=user.card.card_id if user.card else None,
        action="사원증 신청을 통한 계정 생성",
        after_value=None,
        actor=actor,
    )
    db.session.add(log)

    return user


def submit_application(name: str, employee_number: str, department: str, position: str, note: str = None):
    """
    신청서를 접수한다. note가 비어있으면 즉시 자동 승인 처리한다.
    Returns: (CardApplication, auto_approved: bool)
    """
    name = (name or "").strip()
    employee_number = (employee_number or "").strip()
    department = (department or "").strip()
    position = (position or "").strip()
    note = (note or "").strip() or None

    if not name or not employee_number or not department or not position:
        raise ApplicationError("이름, 사번, 부서, 직책은 모두 필수입니다.")

    if User.query.filter_by(username=employee_number).first():
        raise ApplicationError(f"사번 '{employee_number}'은(는) 이미 등록되어 있습니다.")

    existing_pending = CardApplication.query.filter_by(
        employee_number=employee_number, status=STATUS_PENDING
    ).first()
    if existing_pending:
        raise ApplicationError("이미 해당 사번으로 검토 대기 중인 신청이 있습니다.")

    application = CardApplication(
        name=name,
        employee_number=employee_number,
        department=department,
        position=position,
        note=note,
        status=STATUS_PENDING,
    )
    db.session.add(application)
    db.session.flush()

    auto_approved = False
    if not note:
        user = _create_user_from_application(application, actor=ACTOR_SYSTEM)
        application.status = STATUS_APPROVED
        application.resulting_user_id = user.id
        application.reviewed_by = ACTOR_SYSTEM
        from datetime import datetime
        application.reviewed_at = datetime.utcnow()
        auto_approved = True

    db.session.commit()
    return application, auto_approved


def approve_application(application_id: int, actor: str):
    application = CardApplication.query.get(application_id)
    if not application:
        raise ApplicationError("신청 내역을 찾을 수 없습니다.")
    if application.status != STATUS_PENDING:
        raise ApplicationError("검토 대기 상태인 신청만 승인할 수 있습니다.")

    from datetime import datetime

    user = _create_user_from_application(application, actor=actor)
    application.status = STATUS_APPROVED
    application.resulting_user_id = user.id
    application.reviewed_by = actor
    application.reviewed_at = datetime.utcnow()
    db.session.commit()
    return application


def reject_application(application_id: int, actor: str, reason: str = None):
    application = CardApplication.query.get(application_id)
    if not application:
        raise ApplicationError("신청 내역을 찾을 수 없습니다.")
    if application.status != STATUS_PENDING:
        raise ApplicationError("검토 대기 상태인 신청만 반려할 수 있습니다.")

    from datetime import datetime

    application.status = STATUS_REJECTED
    application.reject_reason = (reason or "").strip() or None
    application.reviewed_by = actor
    application.reviewed_at = datetime.utcnow()
    db.session.commit()
    return application
