from flask import Blueprint, render_template, redirect, url_for, session

from utils.decorators import login_required, admin_required, get_current_user

bp = Blueprint("pages", __name__)


@bp.get("/")
def index():
    if not session.get("user_id"):
        return redirect(url_for("pages.login_page"))
    if session.get("role") == "admin":
        return redirect(url_for("pages.admin_dashboard_page"))
    return redirect(url_for("pages.employee_dashboard_page"))


@bp.get("/login")
def login_page():
    if session.get("user_id"):
        return redirect(url_for("pages.index"))
    return render_template("login.html")


@bp.get("/admin/dashboard")
@admin_required
def admin_dashboard_page():
    return render_template("admin/dashboard.html", active="dashboard")


@bp.get("/admin/users")
@admin_required
def admin_users_page():
    return render_template("admin/users.html", active="users")


@bp.get("/admin/cards")
@admin_required
def admin_cards_page():
    return render_template("admin/cards.html", active="cards")


@bp.get("/admin/access")
@admin_required
def admin_access_page():
    return render_template("admin/access.html", active="access")


@bp.get("/admin/policies")
@admin_required
def admin_policies_page():
    return render_template("admin/policies.html", active="policies")


@bp.get("/admin/audit-logs")
@admin_required
def admin_audit_logs_page():
    return render_template("admin/audit_logs.html", active="audit")


@bp.get("/employee/dashboard")
@login_required
def employee_dashboard_page():
    user = get_current_user()
    if user.is_admin():
        return redirect(url_for("pages.admin_dashboard_page"))
    return render_template("employee/dashboard.html", user=user)
