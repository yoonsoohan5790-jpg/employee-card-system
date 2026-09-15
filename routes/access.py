from flask import Blueprint, request, jsonify, session

from extensions import db
from models.access_area import AccessArea
from models.access_policy import AccessPolicy
from utils.decorators import admin_required

bp = Blueprint("access", __name__, url_prefix="/api")


@bp.get("/access-areas")
@admin_required
def list_access_areas():
    areas = AccessArea.query.order_by(AccessArea.id.asc()).all()
    return jsonify([a.to_dict() for a in areas])


@bp.post("/access-areas")
@admin_required
def create_access_area():
    data = request.get_json(force=True)
    if not data.get("area_code") or not data.get("area_name"):
        return jsonify({"error": "area_code, area_name 값은 필수입니다."}), 400
    if AccessArea.query.filter_by(area_code=data["area_code"]).first():
        return jsonify({"error": "이미 존재하는 구역 코드입니다."}), 400

    area = AccessArea(
        area_code=data["area_code"],
        area_name=data["area_name"],
        description=data.get("description"),
        active=data.get("active", True),
    )
    db.session.add(area)
    db.session.commit()
    return jsonify(area.to_dict()), 201


@bp.get("/access-policies")
@admin_required
def list_access_policies():
    policies = AccessPolicy.query.order_by(AccessPolicy.department.asc(), AccessPolicy.position.asc()).all()
    return jsonify([p.to_dict() for p in policies])


@bp.post("/access-policies")
@admin_required
def create_access_policy():
    data = request.get_json(force=True)
    required = ["department", "position", "area_id"]
    for f in required:
        if data.get(f) is None:
            return jsonify({"error": f"{f} 값은 필수입니다."}), 400

    existing = AccessPolicy.query.filter_by(
        department=data["department"], position=data["position"], area_id=data["area_id"]
    ).first()
    if existing:
        existing.allowed = bool(data.get("allowed", False))
        db.session.commit()
        return jsonify(existing.to_dict())

    policy = AccessPolicy(
        department=data["department"],
        position=data["position"],
        area_id=data["area_id"],
        allowed=bool(data.get("allowed", False)),
    )
    db.session.add(policy)
    db.session.commit()
    return jsonify(policy.to_dict()), 201


@bp.put("/access-policies/<int:policy_id>")
@admin_required
def update_access_policy(policy_id):
    policy = AccessPolicy.query.get_or_404(policy_id)
    data = request.get_json(force=True)
    if "allowed" in data:
        policy.allowed = bool(data["allowed"])
    if "department" in data:
        policy.department = data["department"]
    if "position" in data:
        policy.position = data["position"]
    if "area_id" in data:
        policy.area_id = data["area_id"]
    db.session.commit()
    return jsonify(policy.to_dict())


@bp.delete("/access-policies/<int:policy_id>")
@admin_required
def delete_access_policy(policy_id):
    policy = AccessPolicy.query.get_or_404(policy_id)
    db.session.delete(policy)
    db.session.commit()
    return jsonify({"message": "삭제되었습니다."})
