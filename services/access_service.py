import json
from datetime import date, datetime

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


def set_manual_access(user, area_id: int, allowed: bool, actor: str, reason: str = None, expires_at=None):
    """
    관리자가 개별 조직원의 출입권한을 부서/직급 정책과 다르게 수동으로 예외처리한다.
    사유(reason)와 적용 기간(expires_at, 이 날짜까지만 유효)을 함께 남긴다.
    expires_at을 지정하지 않으면 별도 만료 없이 무기한 적용된다.
    """
    grant = UserAccess.query.filter_by(user_id=user.id, area_id=area_id).first()
    before = grant.to_dict() if grant else None

    if grant is None:
        grant = UserAccess(
            user_id=user.id, area_id=area_id, allowed=allowed, source=SOURCE_MANUAL,
            reason=reason, expires_at=expires_at,
        )
        db.session.add(grant)
    else:
        grant.allowed = allowed
        grant.source = SOURCE_MANUAL
        grant.reason = reason
        grant.expires_at = expires_at
        grant.updated_at = datetime.utcnow()

    db.session.flush()

    _log(
        user_id=user.id,
        card_id=user.card.card_id if user.card else None,
        action="출입권한 예외처리",
        before=before,
        after=grant.to_dict(),
        actor=actor,
        detail=reason,
    )
    return grant


def list_manual_exceptions():
    """정책과 다르게 수동으로 예외처리된 출입권한 목록 전체를 반환한다."""
    return (
        UserAccess.query.filter_by(source=SOURCE_MANUAL)
        .order_by(UserAccess.updated_at.desc())
        .all()
    )


def revert_expired_exceptions(actor=ACTOR_SYSTEM):
    """적용 기간(expires_at)이 지난 예외처리를 부서/직급 정책 값으로 되돌린다."""
    from models.user import User

    today = date.today()
    expired = UserAccess.query.filter(
        UserAccess.source == SOURCE_MANUAL,
        UserAccess.expires_at.isnot(None),
        UserAccess.expires_at < today,
    ).all()

    reverted_ids = []
    for grant in expired:
        user = User.query.get(grant.user_id)
        if not user:
            continue
        policy_map = get_policy_map(user.department, user.position)
        expected = bool(policy_map.get(grant.area_id, False))
        before = grant.to_dict()

        grant.allowed = expected
        grant.source = SOURCE_POLICY
        grant.reason = None
        grant.expires_at = None
        grant.updated_at = datetime.utcnow()
        db.session.flush()

        _log(
            user_id=grant.user_id,
            card_id=user.card.card_id if user.card else None,
            action="출입권한 예외처리 기간 만료 (정책으로 복귀)",
            before=before,
            after=grant.to_dict(),
            actor=actor,
        )
        reverted_ids.append(grant.id)

    if reverted_ids:
        db.session.commit()
    return reverted_ids


def get_user_access_status(user):
    """단일 사용자용 편의 함수. 여러 명을 동시에 계산할 때는 get_access_status_bulk를 사용할 것."""
    return get_access_status_bulk([user])[user.id]


def get_access_status_bulk(users):
    """
    여러 조직원의 출입권한 상태(정상/주의/중지/위험)를 쿼리 수를 늘리지 않고 한 번에 계산한다.
    (스펙 17조) 사용자 수만큼 쿼리가 늘어나는 N+1 문제를 피하기 위해 대시보드/목록 화면에서 사용한다.

    - 위험: 퇴사/휴직인데 허용된 권한이 남아있음
    - 중지: 퇴사/휴직 상태이며 권한이 정상적으로 모두 회수된 상태
    - 주의: 재직 중이나 부서/직급 정책과 다른 권한(수동 변경 등)이 존재
    - 정상: 재직 중이며 정책과 일치
    """
    from models.user import EMPLOYMENT_STATUS_ACTIVE

    users = list(users)
    user_ids = [u.id for u in users]

    grants_by_user = {}
    if user_ids:
        all_grants = UserAccess.query.filter(UserAccess.user_id.in_(user_ids)).all()
        for g in all_grants:
            grants_by_user.setdefault(g.user_id, []).append(g)

    policy_rows = AccessPolicy.query.all()
    policy_map_by_dept_position = {}
    for row in policy_rows:
        key = (row.department, row.position)
        policy_map_by_dept_position.setdefault(key, {})[row.area_id] = row.allowed

    statuses = {}
    for user in users:
        grants = grants_by_user.get(user.id, [])

        if user.employment_status != EMPLOYMENT_STATUS_ACTIVE:
            statuses[user.id] = "위험" if any(g.allowed for g in grants) else "중지"
            continue

        policy_map = policy_map_by_dept_position.get((user.department, user.position), {})
        status = "정상"
        for g in grants:
            expected = bool(policy_map.get(g.area_id, False))
            if g.allowed != expected:
                status = "주의"
                break
        statuses[user.id] = status

    return statuses


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
