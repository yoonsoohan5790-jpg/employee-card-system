"""
Gmail SMTP 발송 모듈. (260915_mailsender 스킬 기반, 이 프로젝트용으로 배치)

필요한 환경변수 (.env):
    MAIL_SENDER_EMAIL         발신자 Gmail 주소
    MAIL_SENDER_APP_PASSWORD  Gmail 앱 비밀번호 (일반 로그인 비밀번호 아님)
"""
import smtplib
import mimetypes
from email.message import EmailMessage
from pathlib import Path

from flask import current_app

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def send_email(to, subject, body, attachments=None, cc=None, bcc=None, html=False):
    """Gmail SMTP(STARTTLS)로 이메일을 발송한다. 자격증명은 앱 설정(.env)에서 읽는다."""
    sender_email = current_app.config.get("MAIL_SENDER_EMAIL")
    app_password = current_app.config.get("MAIL_SENDER_APP_PASSWORD")

    if not sender_email or not app_password:
        raise RuntimeError(
            "MAIL_SENDER_EMAIL / MAIL_SENDER_APP_PASSWORD가 설정되어 있지 않습니다. "
            ".env 파일에 등록한 뒤 다시 시도하세요."
        )

    to_list = _as_list(to)
    cc_list = _as_list(cc)
    bcc_list = _as_list(bcc)

    if not to_list:
        raise ValueError("받는사람(to)이 최소 1명 이상이어야 합니다.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    if html:
        msg.set_content("이 메일은 HTML 형식입니다. HTML을 지원하는 메일 클라이언트로 확인해주세요.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    for path in attachments or []:
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"첨부파일을 찾을 수 없습니다: {path}")
        mime_type, _ = mimetypes.guess_type(file_path.name)
        maintype, subtype = (mime_type.split("/", 1) if mime_type else ("application", "octet-stream"))
        with open(file_path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=file_path.name)

    all_recipients = to_list + cc_list + bcc_list

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg, from_addr=sender_email, to_addrs=all_recipients)

    return {"status": "ok", "to": to_list, "cc": cc_list, "bcc": bcc_list}
