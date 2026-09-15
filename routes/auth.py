from flask import Blueprint, request, jsonify, session

from models.user import User

bp = Blueprint("auth", __name__, url_prefix="/api")


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "아이디와 비밀번호를 입력해주세요."}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401

    session.permanent = True
    session["user_id"] = user.id
    session["role"] = user.role
    session["name"] = user.name

    return jsonify({
        "message": "로그인 성공",
        "user": user.to_dict(),
        "redirect": "/admin/dashboard" if user.is_admin() else "/employee/dashboard",
    })


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "로그아웃 되었습니다."})
