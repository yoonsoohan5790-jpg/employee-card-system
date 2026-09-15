"""
'권한 이상' 계정에 대한 알림 메일 조합 + 발송.
"""
from flask import current_app

from models.user_access import UserAccess
from services import mail_sender
from services.link_token import generate_suspend_token

STATUS_DESCRIPTIONS = {
    "위험": "퇴사 또는 휴직 상태인데 출입권한이 남아있는 <strong style=\"color:#dc2626;\">위험</strong> 상태입니다.",
    "주의": "현재 부서/직급 정책과 다른 출입권한이 적용되어 있는 <strong style=\"color:#d97706;\">주의</strong> 상태입니다.",
}


def _allowed_area_names(user):
    grants = UserAccess.query.filter_by(user_id=user.id, allowed=True).all()
    return [g.area.area_name for g in grants if g.area]


def build_alert_email(user, access_status, base_url):
    """제목/HTML 본문과 1회성 중지 링크를 만들어 반환한다."""
    allowed_areas = _allowed_area_names(user)
    areas_html = (
        "".join(f"<li>{name}</li>" for name in allowed_areas)
        if allowed_areas
        else "<li>(현재 허용된 구역 없음)</li>"
    )

    token = generate_suspend_token(user.id)
    suspend_link = f"{base_url.rstrip('/')}/cards/suspend-via-link?token={token}"
    dashboard_link = f"{base_url.rstrip('/')}/admin/access"

    subject = f"[사원증 관리 시스템] 권한 이상 계정 발생 - {user.name}({user.department}/{user.position}) 확인 필요"

    description = STATUS_DESCRIPTIONS.get(access_status, "출입권한 상태를 확인해주세요.")

    body = f"""
    <div style="font-family:'Segoe UI',sans-serif; max-width:560px; margin:0 auto; color:#111827;">
      <h2 style="color:#dc2626;">⚠ 권한 이상 계정이 발견되었습니다</h2>
      <p>사원증 관리 시스템에서 아래 조직원의 출입권한 상태를 점검한 결과, {description}</p>

      <table style="width:100%; border-collapse:collapse; margin:16px 0;">
        <tr><td style="padding:6px 0; color:#6b7280; width:110px;">이름</td><td>{user.name}</td></tr>
        <tr><td style="padding:6px 0; color:#6b7280;">부서 / 직급</td><td>{user.department} / {user.position}</td></tr>
        <tr><td style="padding:6px 0; color:#6b7280;">재직 상태</td><td>{user.employment_status}</td></tr>
        <tr><td style="padding:6px 0; color:#6b7280;">권한 상태</td><td>{access_status}</td></tr>
        <tr><td style="padding:6px 0; color:#6b7280; vertical-align:top;">현재 허용된 구역</td><td><ul style="margin:4px 0; padding-left:18px;">{areas_html}</ul></td></tr>
      </table>

      <div style="margin:24px 0;">
        <a href="{suspend_link}"
           style="background:#dc2626; color:#fff; padding:12px 20px; border-radius:6px; text-decoration:none; font-weight:bold; display:inline-block;">
          지금 즉시 사원증 중지 + 출입권한 회수
        </a>
      </div>

      <p style="font-size:13px; color:#6b7280;">
        위 버튼을 누르면 클릭 확인 페이지로 이동하며, 그곳에서 한 번 더 확인 후 처리됩니다.
        (링크는 48시간 동안 유효합니다.)
      </p>
      <p style="font-size:13px; color:#6b7280;">
        전체 현황은 관리자 대시보드에서도 확인할 수 있습니다:
        <a href="{dashboard_link}">{dashboard_link}</a>
      </p>
      <hr style="border:none; border-top:1px solid #e5e7eb; margin:24px 0;">
      <p style="font-size:12px; color:#9ca3af;">본 메일은 사원증 관리 시스템에서 자동 발송되었습니다.</p>
    </div>
    """

    return subject, body


def send_anomaly_alert(user, access_status, base_url):
    recipient = current_app.config.get("MAIL_ALERT_RECIPIENT")
    if not recipient:
        raise RuntimeError("MAIL_ALERT_RECIPIENT(또는 MAIL_SENDER_EMAIL)가 설정되어 있지 않습니다.")

    subject, body = build_alert_email(user, access_status, base_url)
    return mail_sender.send_email(to=recipient, subject=subject, body=body, html=True)
