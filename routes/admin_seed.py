from flask import Blueprint, request, jsonify, current_app

from seed import seed_data
import generate_bulk_test_data

bp = Blueprint("admin_seed", __name__, url_prefix="/api")


def _check_seed_key():
    token = request.headers.get("X-Seed-Key")
    return bool(token) and token == current_app.config["SECRET_KEY"]


@bp.post("/seed-once")
def seed_once():
    """
    배포 환경(Supabase 등 외부 DB)에 최초 1회 초기 데이터를 넣기 위한 엔드포인트.
    SECRET_KEY와 동일한 값을 X-Seed-Key 헤더로 보내야 실행되며,
    이미 데이터가 있으면 아무 작업도 하지 않는다.
    """
    if not _check_seed_key():
        return jsonify({"error": "unauthorized"}), 403

    result = seed_data()
    return jsonify(result)


@bp.post("/seed-bulk")
def seed_bulk():
    """
    배포 환경(Supabase 등 외부 DB)에 무작위 대량 테스트 조직원을 추가하는 엔드포인트.
    DB 접속 정보를 직접 다루지 않고도 원격 DB에 데이터를 넣기 위해 사용한다.
    SECRET_KEY와 동일한 값을 X-Seed-Key 헤더로 보내야 실행된다.
    호출할 때마다 계속 추가되므로 반복 호출에 주의한다.
    """
    if not _check_seed_key():
        return jsonify({"error": "unauthorized"}), 403

    count = int((request.get_json(silent=True) or {}).get("count", 800))
    result = generate_bulk_test_data.generate(count)
    return jsonify(result)
