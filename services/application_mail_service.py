"""
검토가 필요한(기타사항이 있는) 사원증 신청이 접수되면 관리자에게 알림 메일을 보낸다.
260915_mailsender 스킬 기반 services/mail_sender.py를 그대로 재사용한다.
"""
from flask import current_app

from services import mail_sender


def build_review_alert_email(application, base_url):
    review_link = f"{base_url.rstrip('/')}/admin/applications"

    subject = f"[사원증 관리 시스템] 사원증 신청 검토 필요 - {application.name}({application.department}/{application.position})"

    body = f"""
    <div style="font-family:'Segoe UI',sans-serif; max-width:560px; margin:0 auto; color:#111827;">
      <h2 style="color:#d97706;">📝 검토가 필요한 사원증 신청이 접수되었습니다</h2>
      <p>기타사항이 포함된 신청은 자동 발급되지 않고 관리자 검토를 거칩니다.</p>

      <table style="width:100%; border-collapse:collapse; margin:16px 0;">
        <tr><td style="padding:6px 0; color:#6b7280; width:100px;">이름</td><td>{application.name}</td></tr>
        <tr><td style="padding:6px 0; color:#6b7280;">사번</td><td>{application.employee_number}</td></tr>
        <tr><td style="padding:6px 0; color:#6b7280;">부서 / 직책</td><td>{application.department} / {application.position}</td></tr>
        <tr><td style="padding:6px 0; color:#6b7280; vertical-align:top;">기타사항</td><td>{application.note}</td></tr>
      </table>

      <div style="margin:24px 0;">
        <a href="{review_link}"
           style="background:#2563eb; color:#fff; padding:12px 20px; border-radius:6px; text-decoration:none; font-weight:bold; display:inline-block;">
          관리자 화면에서 검토하기
        </a>
      </div>

      <hr style="border:none; border-top:1px solid #e5e7eb; margin:24px 0;">
      <p style="font-size:12px; color:#9ca3af;">본 메일은 사원증 관리 시스템에서 자동 발송되었습니다.</p>
    </div>
    """
    return subject, body


def send_review_alert(application, base_url):
    recipient = current_app.config.get("MAIL_ALERT_RECIPIENT")
    if not recipient:
        # 메일 미설정 상태에서도 신청 접수 자체는 실패하면 안 되므로 조용히 건너뛴다.
        current_app.logger.warning("MAIL_ALERT_RECIPIENT 미설정 - 신청 검토 알림 메일을 보내지 않았습니다.")
        return None

    subject, body = build_review_alert_email(application, base_url)
    return mail_sender.send_email(to=recipient, subject=subject, body=body, html=True)
