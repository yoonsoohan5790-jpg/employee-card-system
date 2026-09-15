import json
from datetime import date, datetime

from extensions import db
from models.card import Card, CARD_STATUS_ACTIVE, CARD_STATUS_SUSPENDED, CARD_STATUS_REVOKED
from models.audit_log import AuditLog, ACTOR_SYSTEM
from services import access_service


def generate_card_id():
    """CARD-YYYY-000001 형식의 고유 사원증 번호를 생성한다."""
    year = date.today().year
    prefix = f"CARD-{year}-"
    last = (
        Card.query.filter(Card.card_id.like(f"{prefix}%"))
        .order_by(Card.card_id.desc())
        .first()
    )
    if last:
        last_seq = int(last.card_id.split("-")[-1])
        seq = last_seq + 1
    else:
        seq = 1
    return f"{prefix}{seq:06d}"


def issue_card(user, actor=ACTOR_SYSTEM):
    """신규(또는 재발급) 사원증을 발급하고 부서/직급 기준 출입권한을 자동 부여한다."""
    if user.card is not None:
        return reissue_card(user, actor=actor)

    card = Card(
        card_id=generate_card_id(),
        issue_date=date.today(),
        status=CARD_STATUS_ACTIVE,
    )
    user.card = card  # 관계로 직접 연결해 user.card 캐시가 즉시 최신 상태를 반영하도록 한다.
    db.session.add(card)
    db.session.flush()

    _log(user.id, card.card_id, "사원증 발급", None, card.to_dict(), actor)

    access_service.apply_policy_for_user(user, actor=actor)
    return card


def reissue_card(user, actor=ACTOR_SYSTEM):
    """기존 사원증을 폐기하고 새 번호로 재발급한다."""
    old_card = user.card
    before = old_card.to_dict() if old_card else None

    if old_card:
        old_card.status = CARD_STATUS_REVOKED
        old_card.updated_at = datetime.utcnow()
        db.session.flush()
        _log(user.id, old_card.card_id, "사원증 폐기(재발급)", before, old_card.to_dict(), actor)
        db.session.delete(old_card)
        db.session.flush()

    new_card = Card(
        card_id=generate_card_id(),
        issue_date=date.today(),
        status=CARD_STATUS_ACTIVE,
    )
    user.card = new_card
    db.session.add(new_card)
    db.session.flush()
    _log(user.id, new_card.card_id, "사원증 재발급", before, new_card.to_dict(), actor)

    access_service.apply_policy_for_user(user, actor=actor)
    return new_card


def activate_card(user, actor=ACTOR_SYSTEM, reapply_access=True):
    card = user.card
    if card is None:
        return issue_card(user, actor=actor)
    before = card.to_dict()
    card.status = CARD_STATUS_ACTIVE
    card.updated_at = datetime.utcnow()
    db.session.flush()
    _log(user.id, card.card_id, "사원증 활성화", before, card.to_dict(), actor)

    if reapply_access:
        access_service.apply_policy_for_user(user, actor=actor)
    return card


def suspend_card(user, actor=ACTOR_SYSTEM, reason=None, revoke_access=True):
    card = user.card
    if card is None:
        return None
    before = card.to_dict()
    card.status = CARD_STATUS_SUSPENDED
    card.updated_at = datetime.utcnow()
    db.session.flush()
    action = "사원증 중지" if not reason else f"사원증 중지 ({reason})"
    _log(user.id, card.card_id, action, before, card.to_dict(), actor)

    if revoke_access:
        access_service.revoke_all_access(user, actor=actor, reason=reason or "사원증 중지")
    return card


def revoke_card(user, actor=ACTOR_SYSTEM):
    card = user.card
    if card is None:
        return None
    before = card.to_dict()
    card.status = CARD_STATUS_REVOKED
    card.updated_at = datetime.utcnow()
    db.session.flush()
    _log(user.id, card.card_id, "사원증 폐기", before, card.to_dict(), actor)

    access_service.revoke_all_access(user, actor=actor, reason="사원증 폐기")
    return card


def _log(user_id, card_id, action, before, after, actor):
    log = AuditLog(
        user_id=user_id,
        card_id=card_id,
        action=action,
        before_value=json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        after_value=json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
        actor=actor,
    )
    db.session.add(log)
