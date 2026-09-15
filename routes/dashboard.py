from flask import Blueprint, jsonify

from models.user import User, EMPLOYMENT_STATUS_ACTIVE, EMPLOYMENT_STATUS_LEAVE, EMPLOYMENT_STATUS_RESIGNED
from models.card import Card, CARD_STATUSES, CARD_STATUS_LABELS
from models.access_area import AccessArea
from models.user_access import UserAccess
from services import access_service, employment_service
from utils.decorators import admin_required

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/summary")
@admin_required
def summary():
    # 서버리스 환경 등 상시 스케줄러가 없는 경우를 대비해 대시보드 조회 시점에
    # 휴직 종료 체크 + 예외처리 기간 만료 체크를 함께 수행한다.
    employment_service.check_leave_end_dates()
    access_service.revert_expired_exceptions()

    total_users = User.query.count()
    active_cards = Card.query.filter_by(status="active").count()
    suspended_cards = Card.query.filter_by(status="suspended").count()

    users = User.query.all()
    status_by_user = access_service.get_access_status_bulk(users)
    anomaly_count = sum(1 for status in status_by_user.values() if status in ("주의", "위험"))

    return jsonify({
        "total_users": total_users,
        "active_cards": active_cards,
        "suspended_cards": suspended_cards,
        "anomaly_count": anomaly_count,
    })


@bp.get("/cards")
@admin_required
def cards_status():
    counts = {status: Card.query.filter_by(status=status).count() for status in CARD_STATUSES}
    return jsonify({
        "labels": [CARD_STATUS_LABELS[s] for s in CARD_STATUSES],
        "values": [counts[s] for s in CARD_STATUSES],
        "raw": counts,
    })


@bp.get("/departments")
@admin_required
def departments_status():
    users = User.query.all()
    cards_by_user = {c.user_id: c for c in Card.query.all()}

    by_dept = {}
    for u in users:
        if not u.department:
            continue
        bucket = by_dept.setdefault(u.department, {"total": 0, "active": 0, "suspended": 0})
        bucket["total"] += 1
        card = cards_by_user.get(u.id)
        if card and card.status == "active":
            bucket["active"] += 1
        elif card and card.status == "suspended":
            bucket["suspended"] += 1

    result = [
        {"department": dept, "total": v["total"], "active": v["active"], "suspended": v["suspended"]}
        for dept, v in by_dept.items()
    ]
    return jsonify(result)


@bp.get("/access")
@admin_required
def access_status():
    users = User.query.order_by(User.id.asc()).all()
    areas = AccessArea.query.filter_by(active=True).order_by(AccessArea.id.asc()).all()

    # 사용자 수만큼 쿼리가 늘어나지 않도록 권한 데이터와 상태를 한 번에 계산한다. (N+1 방지)
    user_ids = [u.id for u in users]
    grants_by_user = {}
    if user_ids:
        for g in UserAccess.query.filter(UserAccess.user_id.in_(user_ids)).all():
            grants_by_user.setdefault(g.user_id, {})[g.area_id] = g.allowed
    status_by_user = access_service.get_access_status_bulk(users)

    result = []
    for u in users:
        grants = grants_by_user.get(u.id, {})
        result.append({
            "user_id": u.id,
            "name": u.name,
            "department": u.department,
            "position": u.position,
            "employment_status": u.employment_status,
            "access_status": status_by_user.get(u.id),
            "areas": [
                {"area_id": a.id, "area_code": a.area_code, "area_name": a.area_name, "allowed": grants.get(a.id, False)}
                for a in areas
            ],
        })
    return jsonify(result)


@bp.get("/alerts")
@admin_required
def alerts():
    users = User.query.all()
    status_by_user = access_service.get_access_status_bulk(users)

    resigned_with_access = []
    leave_with_access = []
    policy_mismatch = []

    for u in users:
        status = status_by_user.get(u.id)
        if status == "위험":
            entry = {"user_id": u.id, "name": u.name, "department": u.department, "position": u.position}
            if u.employment_status == EMPLOYMENT_STATUS_RESIGNED:
                resigned_with_access.append(entry)
            elif u.employment_status == EMPLOYMENT_STATUS_LEAVE:
                leave_with_access.append(entry)
        elif status == "주의":
            policy_mismatch.append({"user_id": u.id, "name": u.name, "department": u.department, "position": u.position})

    return jsonify({
        "resigned_with_access": resigned_with_access,
        "leave_with_access": leave_with_access,
        "policy_mismatch": policy_mismatch,
    })
