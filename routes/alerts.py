from flask import Blueprint, request, jsonify, render_template

from extensions import db
from models.user import User
from services import access_service, card_service, alert_mail_service
from services.link_token import verify_suspend_token
from utils.decorators import admin_required

bp = Blueprint("alerts", __name__)


@bp.post("/api/alerts/notify")
@admin_required
def notify_anomaly():
    """권한 이상 계정에 대한 알림 메일을 발송한다. (관리자가 UI에서 확인 후 호출)"""
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id 값은 필수입니다."}), 400

    user = User.query.get_or_404(user_id)
    status = access_service.get_user_access_status(user)
    if status not in ("위험", "주의"):
        return jsonify({"error": "권한 이상 상태가 아닌 조직원입니다."}), 400

    try:
        base_url = request.url_root
        result = alert_mail_service.send_anomaly_alert(user, status, base_url)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"메일 발송에 실패했습니다: {e}"}), 502

    return jsonify(result)


@bp.get("/cards/suspend-via-link")
def suspend_via_link_confirm():
    """메일의 조치 링크로 들어오면 곧바로 실행하지 않고 확인 화면을 먼저 보여준다.
    (메일 보안 스캐너가 링크를 미리 열어보는 경우에도 실수로 중지되지 않도록 하기 위함)"""
    token = request.args.get("token", "")
    user_id = verify_suspend_token(token)
    if not user_id:
        return render_template("link_result.html", ok=False, message="유효하지 않거나 만료된 링크입니다."), 400

    user = User.query.get(user_id)
    if not user:
        return render_template("link_result.html", ok=False, message="대상 조직원을 찾을 수 없습니다."), 404

    return render_template("link_confirm.html", user=user, token=token)


@bp.post("/cards/suspend-via-link")
def suspend_via_link():
    token = request.form.get("token", "")
    user_id = verify_suspend_token(token)
    if not user_id:
        return render_template("link_result.html", ok=False, message="유효하지 않거나 만료된 링크입니다."), 400

    user = User.query.get(user_id)
    if not user:
        return render_template("link_result.html", ok=False, message="대상 조직원을 찾을 수 없습니다."), 404

    if user.card and user.card.status == "suspended":
        message = f"{user.name}님의 사원증은 이미 중지된 상태입니다."
    else:
        card_service.suspend_card(
            user,
            actor="이메일 링크(관리자 승인)",
            reason="권한 이상 알림 메일을 통한 즉시 중지",
        )
        db.session.commit()
        message = f"{user.name}님의 사원증을 중지하고 모든 출입권한을 회수했습니다."

    return render_template("link_result.html", ok=True, message=message)
