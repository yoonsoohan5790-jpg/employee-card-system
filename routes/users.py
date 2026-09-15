from datetime import datetime, date

from flask import Blueprint, request, jsonify, session

from extensions import db
from models.user import User, EMPLOYMENT_STATUS_ACTIVE, EMPLOYMENT_STATUSES, ROLE_EMPLOYEE, ROLE_ADMIN
from models.card import Card
from models.user_access import UserAccess
from services import card_service, access_service, employment_service
from utils.decorators import login_required, admin_required, get_current_user

bp = Blueprint("users", __name__, url_prefix="/api/users")


def _parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@bp.get("")
@admin_required
def list_users():
    q = User.query
    department = request.args.get("department")
    status = request.args.get("employment_status")
    if department:
        q = q.filter_by(department=department)
    if status:
        q = q.filter_by(employment_status=status)

    users = q.order_by(User.id.asc()).all()

    # 사용자 수만큼 쿼리가 늘어나지 않도록 카드/권한상태를 한 번에 조회한다. (N+1 방지)
    user_ids = [u.id for u in users]
    cards_by_user = {}
    if user_ids:
        for c in Card.query.filter(Card.user_id.in_(user_ids)).all():
            cards_by_user[c.user_id] = c
    status_by_user = access_service.get_access_status_bulk(users)

    result = []
    for u in users:
        d = u.to_dict()
        card = cards_by_user.get(u.id)
        d["card"] = card.to_dict() if card else None
        d["access_status"] = status_by_user.get(u.id)
        result.append(d)
    return jsonify(result)


@bp.get("/<int:user_id>")
@login_required
def get_user(user_id):
    current = get_current_user()
    if not current.is_admin() and current.id != user_id:
        return jsonify({"error": "본인 정보만 조회할 수 있습니다."}), 403

    user = User.query.get_or_404(user_id)
    d = user.to_dict()
    d["card"] = user.card.to_dict() if user.card else None
    if current.is_admin():
        d["access_status"] = access_service.get_user_access_status(user)
    return jsonify(d)


@bp.post("")
@admin_required
def create_user():
    data = request.get_json(force=True)

    required = ["username", "password", "name", "department", "position"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} 값은 필수입니다."}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "이미 존재하는 아이디입니다."}), 400

    user = User(
        username=data["username"],
        name=data["name"],
        department=data["department"],
        position=data["position"],
        email=data.get("email"),
        phone=data.get("phone"),
        hire_date=_parse_date(data.get("hire_date")) or date.today(),
        resign_date=_parse_date(data.get("resign_date")),
        leave_start_date=_parse_date(data.get("leave_start_date")),
        leave_end_date=_parse_date(data.get("leave_end_date")),
        employment_status=data.get("employment_status", EMPLOYMENT_STATUS_ACTIVE),
        role=data.get("role", ROLE_EMPLOYEE) if data.get("role") in (ROLE_EMPLOYEE, ROLE_ADMIN) else ROLE_EMPLOYEE,
    )
    user.set_password(data["password"])

    if user.employment_status not in EMPLOYMENT_STATUSES:
        return jsonify({"error": "재직 상태 값이 올바르지 않습니다."}), 400

    db.session.add(user)
    db.session.flush()

    if user.employment_status == EMPLOYMENT_STATUS_ACTIVE:
        card_service.issue_card(user, actor=session.get("name", "admin"))
    else:
        access_service.apply_policy_for_user(user, actor=session.get("name", "admin"))

    db.session.commit()

    d = user.to_dict()
    d["card"] = user.card.to_dict() if user.card else None
    return jsonify(d), 201


@bp.put("/<int:user_id>")
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(force=True)
    actor = session.get("name", "admin")

    old_department = user.department
    old_position = user.position
    old_status = user.employment_status

    if "name" in data:
        user.name = data["name"]
    if "department" in data:
        user.department = data["department"]
    if "position" in data:
        user.position = data["position"]
    if "email" in data:
        user.email = data["email"]
    if "phone" in data:
        user.phone = data["phone"]
    if "hire_date" in data:
        user.hire_date = _parse_date(data["hire_date"])
    if "resign_date" in data:
        user.resign_date = _parse_date(data["resign_date"])
    if "leave_start_date" in data:
        user.leave_start_date = _parse_date(data["leave_start_date"])
    if "leave_end_date" in data:
        user.leave_end_date = _parse_date(data["leave_end_date"])
    if "employment_status" in data:
        new_status = data["employment_status"]
        if new_status not in EMPLOYMENT_STATUSES:
            return jsonify({"error": "재직 상태 값이 올바르지 않습니다."}), 400
        user.employment_status = new_status
    if "password" in data and data["password"]:
        user.set_password(data["password"])

    user.updated_at = datetime.utcnow()
    db.session.flush()

    new_status = user.employment_status
    dept_or_position_changed = (user.department != old_department) or (user.position != old_position)

    if new_status != old_status:
        employment_service.handle_employment_status_change(user, old_status, new_status, actor=actor)
    elif dept_or_position_changed and new_status == EMPLOYMENT_STATUS_ACTIVE:
        access_service.apply_policy_for_user(user, actor=actor)

    db.session.commit()

    d = user.to_dict()
    d["card"] = user.card.to_dict() if user.card else None
    d["access_status"] = access_service.get_user_access_status(user)
    return jsonify(d)


@bp.delete("/<int:user_id>")
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "삭제되었습니다."})


@bp.get("/<int:user_id>/access")
@login_required
def get_user_access(user_id):
    current = get_current_user()
    if not current.is_admin() and current.id != user_id:
        return jsonify({"error": "본인 정보만 조회할 수 있습니다."}), 403

    user = User.query.get_or_404(user_id)
    grants = UserAccess.query.filter_by(user_id=user.id).all()
    return jsonify({
        "user_id": user.id,
        "employment_status": user.employment_status,
        "access_status": access_service.get_user_access_status(user) if current.is_admin() else None,
        "grants": [g.to_dict() for g in grants],
    })


@bp.put("/<int:user_id>/access")
@admin_required
def update_user_access(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(force=True)
    area_id = data.get("area_id")
    allowed = bool(data.get("allowed"))
    reason = (data.get("reason") or "").strip() or None
    expires_at_raw = (data.get("expires_at") or "").strip() or None

    if area_id is None:
        return jsonify({"error": "area_id 값은 필수입니다."}), 400
    if not reason:
        return jsonify({"error": "예외처리 사유를 입력해주세요."}), 400

    expires_at = None
    if expires_at_raw:
        try:
            expires_at = _parse_date(expires_at_raw)
        except ValueError:
            return jsonify({"error": "적용 기간(종료일) 형식이 올바르지 않습니다."}), 400
        if expires_at < date.today():
            return jsonify({"error": "적용 기간(종료일)은 오늘 이후로 설정해주세요."}), 400

    grant = access_service.set_manual_access(
        user, int(area_id), allowed, actor=session.get("name", "admin"), reason=reason, expires_at=expires_at
    )
    db.session.commit()
    return jsonify(grant.to_dict())
