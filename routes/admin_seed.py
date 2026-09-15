from flask import Blueprint, request, jsonify, current_app

from seed import seed_data

bp = Blueprint("admin_seed", __name__, url_prefix="/api")


@bp.post("/seed-once")
def seed_once():
    """
    배포 환경(Supabase 등 외부 DB)에 최초 1회 초기 데이터를 넣기 위한 엔드포인트.
    SECRET_KEY와 동일한 값을 X-Seed-Key 헤더로 보내야 실행되며,
    이미 데이터가 있으면 아무 작업도 하지 않는다.
    """
    token = request.headers.get("X-Seed-Key")
    if not token or token != current_app.config["SECRET_KEY"]:
        return jsonify({"error": "unauthorized"}), 403

    result = seed_data()
    return jsonify(result)
