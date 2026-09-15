import json
from datetime import datetime

from extensions import db
from models.access_area import AccessArea
from models.access_policy import AccessPolicy
from models.user_access import UserAccess, SOURCE_POLICY, SOURCE_MANUAL
from models.audit_log import AuditLog, ACTOR_SYSTEM


def get_policy_map(department: str, position: str):
    """부서+직급 조합에 해당하는 area_id -> allowed 매핑을 반환한다."""
    rows = AccessPolicy.query.filter_by(department=department, position=position).all()
    return {row.area_id: row.allowed for row in rows}


def apply_policy_for_user(user, actor=ACTOR_SYSTEM):
    """
    조직원의 현재 부서/직급 기준으로 출입권한을 다시 계산해 적용한다.
    기존 권한(수동 포함)은 모두 회수하고 정책에 맞는 권한으로 새로 부여한다. (스펙 10조)
    """
    before = [g.to_dict() for g in UserAccess.query.filter_by(user_id=user.id).all()]

    policy_map = get_policy_map(user.department, user.position)
    areas = AccessArea.query.filter_by(active=True).all()

    UserAccess.query.filter_by(user_id=user.id).delete()

    for area in areas:
        allowed = bool(policy_map.get(area.id, False))
        grant = UserAccess(
            user_id=user.id,
            area_id=area.id,
            allowed=allowed,
            source=SOURCE_POLICY,
        )
        db.session.add(grant)

    db.session.flush()
    after = [g.to_dict() for g in UserAccess.query.filter_by(user_id=user.id).all()]

    _log(
        user_id=user.id,
        card_id=user.card.card_id if user.card else None,
        action="출입권한 정책 적용",
        before=before,
        after=after,
        actor=actor,
    )


def revoke_all_access(user, actor=ACTOR_SYSTEM, reason="사원증 중지"):
    """조직원의 모든 출입권한을 회수한다. (퇴사/휴직 처리 시 사용)"""
    grants = UserAccess.query.filter_by(user_id=user.id).all()
    if not grants:
        return
    before = [g.to_dict() for g in grants]
    for g in grants:
        g.allowed = False
        g.updated_at = datetime.utcnow()
    db.session.flush()
    after = [g.to_dict() for g in UserAccess.query.filter_by(user_id=user.id).all()]

    _log(
        user_id=user.id,
        card_id=user.card.card_id if user.card else None,
        action="출입권한 전체 회수",
        before=before,
        after=after,
        actor=actor,
        detail=reason,
    )


def set_manual_access(user, area_id: int, allowed: bool, actor: str):
    """관리자가 개별 조직원의 출입권한을 수동으로 수정한다."""
    grant = UserAccess.query.filter_by(user_id=user.id, area_id=area_id).first()
    before = grant.to_dict() if grant else None

    if grant is None:
        grant = UserAccess(user_id=user.id, area_id=area_id, allowed=allowed, source=SOURCE_MANUAL)
        db.session.add(grant)
    else:
        grant.allowed = allowed
        grant.source = SOURCE_MANUAL
        grant.updated_at = datetime.utcnow()

    db.session.flush()

    _log(
        user_id=user.id,
        card_id=user.card.card_id if user.card else None,
        action="출입권한 수동 수정",
        before=before,
        after=grant.to_dict(),
        actor=actor,
    )
    return grant


def get_user_access_status(user):
    """
    조직원의 출입권한 상태(정상/주의/중지/위험)를 판단한다. (스펙 17조)
    - 위험: 퇴사/휴직인데 허용된 권한이 남아있음
    - 중지: 퇴사/휴직 상태이며 권한이 정상적으로 모두 회수된 상태
    - 주의: 재직 중이나 부서/직급 정책과 다른 권한(수동 변경 등)이 존재
    - 정상: 재직 중이며 정책과 일치
    """
    from models.user import EMPLOYMENT_STATUS_ACTIVE

    grants = UserAccess.query.filter_by(user_id=user.id).all()

    if user.employment_status != EMPLOYMENT_STATUS_ACTIVE:
        if any(g.allowed for g in grants):
            return "위험"
        return "중지"

    policy_map = get_policy_map(user.department, user.position)
    for g in grants:
        expected = bool(policy_map.get(g.area_id, False))
        if g.allowed != expected:
            return "주의"

    return "정상"


def _log(user_id, card_id, action, before, after, actor, detail=None):
    log = AuditLog(
        user_id=user_id,
        card_id=card_id,
        action=action,
        before_value=json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        after_value=json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
        actor=actor,
    )
    if detail:
        log.action = f"{action} ({detail})"
    db.session.add(log)
