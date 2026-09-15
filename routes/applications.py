from flask import Blueprint, request, jsonify, render_template, session, current_app

from models.card_application import CardApplication, STATUS_PENDING
from services import application_service, application_mail_service
from services.application_service import ApplicationError
from utils.decorators import admin_required

bp = Blueprint("applications", __name__)


@bp.get("/apply")
def apply_page():
    """로그인 없이 접근 가능한 사원증 신청 페이지."""
    return render_template("apply.html")


@bp.post("/api/card-applications")
def submit_application():
    data = request.get_json(force=True)

    try:
        application, auto_approved = application_service.submit_application(
            name=data.get("name"),
            employee_number=data.get("employee_number"),
            department=data.get("department"),
            position=data.get("position"),
            note=data.get("note"),
        )
    except ApplicationError as e:
        return jsonify({"error": str(e)}), 400

    if not auto_approved:
        try:
            application_mail_service.send_review_alert(application, request.url_root)
        except Exception:
            current_app.logger.exception("사원증 신청 검토 알림 메일 발송 실패")

    return jsonify({
        "auto_approved": auto_approved,
        "application": application.to_dict(),
    }), 201


@bp.get("/api/card-applications")
@admin_required
def list_applications():
    status = request.args.get("status")
    q = CardApplication.query
    if status:
        q = q.filter_by(status=status)
    applications = q.order_by(CardApplication.created_at.desc()).all()
    return jsonify([a.to_dict() for a in applications])


@bp.post("/api/card-applications/<int:application_id>/approve")
@admin_required
def approve_application(application_id):
    try:
        application = application_service.approve_application(
            application_id, actor=session.get("name", "admin")
        )
    except ApplicationError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(application.to_dict())


@bp.post("/api/card-applications/<int:application_id>/reject")
@admin_required
def reject_application(application_id):
    data = request.get_json(silent=True) or {}
    try:
        application = application_service.reject_application(
            application_id, actor=session.get("name", "admin"), reason=data.get("reason")
        )
    except ApplicationError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(application.to_dict())
