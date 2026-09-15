import os

from flask import Flask

from config import Config
from extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from routes.auth import bp as auth_bp
    from routes.users import bp as users_bp
    from routes.cards import bp as cards_bp
    from routes.access import bp as access_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.audit import bp as audit_bp
    from routes.pages import bp as pages_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(cards_bp)
    app.register_blueprint(access_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(pages_bp)

    with app.app_context():
        db.create_all()

    if app.config.get("ENABLE_BACKGROUND_SCHEDULER") and os.environ.get("VERCEL") != "1":
        _start_scheduler(app)

    return app


def _start_scheduler(app):
    """
    로컬 실행 시에만 동작하는 백그라운드 스케줄러.
    휴직 종료일이 지난 조직원을 주기적으로 확인해 사원증을 재활성화한다. (스펙 21조)
    Vercel 같은 서버리스 환경에서는 상시 프로세스가 없으므로 대신
    routes/dashboard.py의 summary API 호출 시점에 동일 로직을 인라인으로 실행한다.
    """
    from apscheduler.schedulers.background import BackgroundScheduler
    from services import employment_service

    scheduler = BackgroundScheduler(daemon=True)

    def job():
        with app.app_context():
            employment_service.check_leave_end_dates()

    scheduler.add_job(job, "interval", minutes=5, next_run_time=None)
    scheduler.start()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
