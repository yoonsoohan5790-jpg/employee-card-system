from functools import wraps

from flask import session, jsonify, redirect, url_for, request

from models.user import User


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "로그인이 필요합니다."}), 401
            return redirect(url_for("pages.login_page"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "로그인이 필요합니다."}), 401
            return redirect(url_for("pages.login_page"))
        if session.get("role") != "admin":
            if request.path.startswith("/api/"):
                return jsonify({"error": "관리자 권한이 필요합니다."}), 403
            return redirect(url_for("pages.employee_dashboard_page"))
        return view(*args, **kwargs)

    return wrapped
