import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _normalize_db_url(url: str) -> str:
    # Supabase/Heroku 스타일 postgres:// 접두사를 SQLAlchemy + psycopg3 드라이버 형식으로 변환
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    _database_url = os.environ.get("DATABASE_URL")
    if _database_url:
        SQLALCHEMY_DATABASE_URI = _normalize_db_url(_database_url)
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "database.db")

    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # 휴직 종료일 도래 시 자동으로 재직/활성 처리할지 여부.
    # False로 두면 관리자가 화면에서 직접 확인 후 활성화해야 한다. (스펙 13조 단서 조항)
    AUTO_REACTIVATE_ON_LEAVE_END = os.environ.get("AUTO_REACTIVATE_ON_LEAVE_END", "true").lower() == "true"

    # 로컬 실행(APScheduler 백그라운드 스레드) 사용 여부.
    # Vercel 같은 서버리스 환경은 상시 실행 스레드를 지원하지 않으므로 비활성화하고,
    # 대신 대시보드/목록 조회 시점에 employment_service.check_leave_end_dates()를 인라인으로 호출한다.
    ENABLE_BACKGROUND_SCHEDULER = os.environ.get("ENABLE_BACKGROUND_SCHEDULER", "true").lower() == "true"
