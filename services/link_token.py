"""
메일에 담을 '1회성 조치 링크'용 서명 토큰.

로그인 없이 이메일 링크만으로 사원증을 중지할 수 있게 해주므로,
위조/재사용을 막기 위해 SECRET_KEY로 서명하고 만료시간을 둔다.
"""
import base64
import hashlib
import hmac
import json
import time

from flask import current_app

DEFAULT_TTL_SECONDS = 60 * 60 * 48  # 48시간


def _b64encode(raw: bytes) -> bytes:
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def _b64decode(data: bytes) -> bytes:
    padded = data + b"=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def _sign(payload_b64: bytes) -> bytes:
    key = current_app.config["SECRET_KEY"].encode()
    return _b64encode(hmac.new(key, payload_b64, hashlib.sha256).digest())


def generate_suspend_token(user_id: int, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    payload = {"user_id": user_id, "exp": int(time.time()) + ttl_seconds}
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_b64 = _sign(payload_b64)
    return (payload_b64 + b"." + sig_b64).decode()


def verify_suspend_token(token: str):
    """유효하면 user_id를, 위조/만료면 None을 반환한다."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig_b64 = token.encode().split(b".", 1)
    except ValueError:
        return None

    expected_sig_b64 = _sign(payload_b64)
    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None

    try:
        payload = json.loads(_b64decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None

    if payload.get("exp", 0) < time.time():
        return None

    return payload.get("user_id")
