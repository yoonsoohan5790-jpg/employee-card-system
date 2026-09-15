from flask import Blueprint, request, jsonify, session

from extensions import db
from models.user import User
from models.card import Card
from services import card_service
from utils.decorators import login_required, admin_required, get_current_user

bp = Blueprint("cards", __name__, url_prefix="/api/cards")


@bp.get("")
@admin_required
def list_cards():
    status = request.args.get("status")
    q = Card.query
    if status:
        q = q.filter_by(status=status)
    cards = q.order_by(Card.id.asc()).all()
    result = []
    for c in cards:
        d = c.to_dict()
        d["user_name"] = c.user.name if c.user else None
        d["department"] = c.user.department if c.user else None
        d["position"] = c.user.position if c.user else None
        d["employment_status"] = c.user.employment_status if c.user else None
        result.append(d)
    return jsonify(result)


@bp.get("/<int:card_pk>")
@login_required
def get_card(card_pk):
    card = Card.query.get_or_404(card_pk)
    current = get_current_user()
    if not current.is_admin() and current.id != card.user_id:
        return jsonify({"error": "본인 사원증만 조회할 수 있습니다."}), 403
    return jsonify(card.to_dict())


@bp.post("/issue")
@admin_required
def issue_card():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id 값은 필수입니다."}), 400

    user = User.query.get_or_404(user_id)
    card = card_service.issue_card(user, actor=session.get("name", "admin"))
    db.session.commit()
    return jsonify(card.to_dict()), 201


@bp.put("/<int:card_pk>")
@admin_required
def update_card(card_pk):
    card = Card.query.get_or_404(card_pk)
    data = request.get_json(force=True)
    if "status" in data:
        card.status = data["status"]
    db.session.commit()
    return jsonify(card.to_dict())


@bp.post("/<int:card_pk>/activate")
@admin_required
def activate_card(card_pk):
    card = Card.query.get_or_404(card_pk)
    user = User.query.get(card.user_id)
    card_service.activate_card(user, actor=session.get("name", "admin"))
    db.session.commit()
    return jsonify(user.card.to_dict())


@bp.post("/<int:card_pk>/suspend")
@admin_required
def suspend_card(card_pk):
    card = Card.query.get_or_404(card_pk)
    user = User.query.get(card.user_id)
    reason = (request.get_json(silent=True) or {}).get("reason", "관리자 수동 중지")
    card_service.suspend_card(user, actor=session.get("name", "admin"), reason=reason)
    db.session.commit()
    return jsonify(user.card.to_dict())


@bp.post("/<int:card_pk>/revoke")
@admin_required
def revoke_card(card_pk):
    card = Card.query.get_or_404(card_pk)
    user = User.query.get(card.user_id)
    card_service.revoke_card(user, actor=session.get("name", "admin"))
    db.session.commit()
    return jsonify(user.card.to_dict())
