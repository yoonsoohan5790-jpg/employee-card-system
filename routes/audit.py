from flask import Blueprint, request, jsonify

from models.audit_log import AuditLog
from utils.decorators import admin_required

bp = Blueprint("audit", __name__, url_prefix="/api/audit-logs")


@bp.get("")
@admin_required
def list_audit_logs():
    limit = min(int(request.args.get("limit", 200)), 1000)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return jsonify([l.to_dict() for l in logs])


@bp.get("/<int:user_id>")
@admin_required
def user_audit_logs(user_id):
    logs = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.created_at.desc()).all()
    return jsonify([l.to_dict() for l in logs])
