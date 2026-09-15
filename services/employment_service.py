import json
from datetime import date, datetime

from flask import current_app

from extensions import db
from models.user import (
    User,
    EMPLOYMENT_STATUS_ACTIVE,
    EMPLOYMENT_STATUS_LEAVE,
    EMPLOYMENT_STATUS_RESIGNED,
)
from models.audit_log import AuditLog, ACTOR_SYSTEM
from services import card_service, access_service


def handle_employment_status_change(user, old_status: str, new_status: str, actor=ACTOR_SYSTEM):
    """
    재직 상태 변경에 따라 사원증/출입권한을 자동 처리한다. (스펙 11~13조, 22조)

    - 재직 -> 휴직/퇴사 : 사원증 중지 + 출입권한 전체 회수
    - 휴직 -> 재직        : 사원증 활성화 + 부서/직급 기준 권한 재적용
    - 연차/반차는 employment_status 값 자체가 아니므로(재직/휴직/퇴사 3종) 이 로직의 영향을 받지 않는다.
    """
    if old_status == new_status:
        return

    _log_status_change(user, old_status, new_status, actor)

    if new_status in (EMPLOYMENT_STATUS_LEAVE, EMPLOYMENT_STATUS_RESIGNED):
        card_service.suspend_card(user, actor=actor, reason=f"{new_status} 처리", revoke_access=True)

    elif new_status == EMPLOYMENT_STATUS_ACTIVE and old_status in (
        EMPLOYMENT_STATUS_LEAVE,
        EMPLOYMENT_STATUS_RESIGNED,
    ):
        if user.card is None:
            card_service.issue_card(user, actor=actor)
        else:
            card_service.activate_card(user, actor=actor, reapply_access=True)


def check_leave_end_dates(actor=ACTOR_SYSTEM):
    """
    휴직 종료일이 도래한 휴직자를 찾아 자동으로 재직/활성 처리한다. (스펙 13조)
    config.AUTO_REACTIVATE_ON_LEAVE_END 가 False면 자동 처리하지 않고 목록만 반환한다
    (관리자가 화면에서 직접 확인 후 처리해야 하는 케이스).
    """
    today = date.today()
    candidates = User.query.filter(
        User.employment_status == EMPLOYMENT_STATUS_LEAVE,
        User.leave_end_date.isnot(None),
        User.leave_end_date <= today,
    ).all()

    auto_reactivate = current_app.config.get("AUTO_REACTIVATE_ON_LEAVE_END", True)
    processed = []

    for user in candidates:
        if not auto_reactivate:
            continue
        old_status = user.employment_status
        user.employment_status = EMPLOYMENT_STATUS_ACTIVE
        user.updated_at = datetime.utcnow()
        db.session.flush()
        handle_employment_status_change(user, old_status, EMPLOYMENT_STATUS_ACTIVE, actor=actor)
        processed.append(user.id)

    if processed:
        db.session.commit()

    return {
        "checked_at": today.isoformat(),
        "auto_reactivate": auto_reactivate,
        "candidate_ids": [u.id for u in candidates],
        "processed_ids": processed,
    }


def _log_status_change(user, old_status, new_status, actor):
    log = AuditLog(
        user_id=user.id,
        card_id=user.card.card_id if user.card else None,
        action="인사 상태 변경",
        before_value=json.dumps({"employment_status": old_status}, ensure_ascii=False),
        after_value=json.dumps({"employment_status": new_status}, ensure_ascii=False),
        actor=actor,
    )
    db.session.add(log)
