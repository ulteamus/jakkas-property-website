from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models.admin import Admin

auth_bp = Blueprint("auth", __name__)


def _safe_next_url(value):
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.netloc or parsed.scheme:
        return None
    if not value.startswith("/"):
        return None
    return value


@auth_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    next_url = _safe_next_url(request.args.get("next") or request.form.get("next"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = Admin.get_by_username(username, include_inactive=True)
        if admin and admin.is_active and admin.check_password(password):
            login_user(admin)
            flash("Welcome back!", "success")
            return redirect(next_url or url_for("admin.dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("admin/login.html")


@auth_bp.route("/admin/logout")
@login_required
def admin_logout():
    logout_user()
    session.pop("admin_otp_verified", None)
    session.pop("admin_otp_verified_admin_id", None)
    session.pop("pending_admin_id", None)
    session.pop("pending_admin_next", None)
    session.pop("pending_admin_dev_otp", None)
    flash("Logged out.", "info")
    return redirect(url_for("public.home"))
