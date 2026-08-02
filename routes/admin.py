import os
import uuid
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from database import execute, query_all, query_one
from models import property_model
from models.user import User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    from functools import wraps

    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)

    return decorated


@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "users": query_one("SELECT COUNT(*) AS c FROM users")["c"],
        "properties": query_one("SELECT COUNT(*) AS c FROM properties")["c"],
        "visits": query_one("SELECT COUNT(*) AS c FROM site_visits")["c"],
        "pending_visits": query_one(
            "SELECT COUNT(*) AS c FROM site_visits WHERE status = 'pending'"
        )["c"],
    }
    recent_visits = query_all(
        """SELECT sv.*, u.username, p.title AS property_title
           FROM site_visits sv
           JOIN users u ON u.id = sv.user_id
           JOIN properties p ON p.id = sv.property_id
           ORDER BY sv.created_at DESC LIMIT 10"""
    )
    return render_template("admin/dashboard.html", stats=stats, recent_visits=recent_visits)


@admin_bp.route("/properties")
@admin_required
def properties_list():
    props = property_model.get_all()
    return render_template("admin/properties.html", properties=props)


@admin_bp.route("/properties/add", methods=["GET", "POST"])
@admin_required
def add_property():
    if request.method == "POST":
        data = _form_to_property_data(request.form)
        prop = property_model.create(data, created_by=current_user.id)
        _handle_image_upload(request, prop["id"])
        flash("Property added.", "success")
        return redirect(url_for("admin.properties_list"))
    return render_template("admin/property_form.html", property=None)


@admin_bp.route("/properties/<int:property_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_property(property_id):
    prop = property_model.get_by_id(property_id)
    if not prop:
        abort(404)
    if request.method == "POST":
        data = _form_to_property_data(request.form)
        property_model.update(property_id, data)
        _handle_image_upload(request, property_id)
        flash("Property updated.", "success")
        return redirect(url_for("admin.properties_list"))
    return render_template("admin/property_form.html", property=prop)


@admin_bp.route("/properties/<int:property_id>/delete", methods=["POST"])
@admin_required
def delete_property(property_id):
    property_model.delete(property_id)
    flash("Property deleted.", "info")
    return redirect(url_for("admin.properties_list"))


@admin_bp.route("/users")
@admin_required
def users_list():
    users = query_all("SELECT id, username, email, full_name, role, created_at FROM users")
    return render_template("admin/users.html", users=users)


@admin_bp.route("/visits/<int:visit_id>/status", methods=["POST"])
@admin_required
def update_visit_status(visit_id):
    status = request.form.get("status", "pending")
    execute("UPDATE site_visits SET status = %s WHERE id = %s", (status, visit_id))
    flash("Visit status updated.", "success")
    return redirect(url_for("admin.dashboard"))


def _form_to_property_data(form):
    amenities = [a.strip() for a in form.get("amenities", "").split(",") if a.strip()]
    return {
        "title": form.get("title"),
        "description": form.get("description"),
        "property_type": form.get("property_type"),
        "listing_type": form.get("listing_type", "sale"),
        "city": form.get("city"),
        "locality": form.get("locality"),
        "address": form.get("address"),
        "bedrooms": int(form.get("bedrooms") or 0),
        "bathrooms": int(form.get("bathrooms") or 0),
        "area_sqft": float(form.get("area_sqft")),
        "price": float(form.get("price")),
        "year_built": int(form["year_built"]) if form.get("year_built") else None,
        "amenities": amenities,
        "status": form.get("status", "available"),
    }


def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg"})


def _handle_image_upload(request, property_id):
    files = request.files.getlist("images")
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    for i, f in enumerate(files):
        if f and f.filename and _allowed_file(f.filename):
            ext = secure_filename(f.filename).rsplit(".", 1)[-1]
            name = f"{property_id}_{uuid.uuid4().hex[:8]}.{ext}"
            path = upload_dir / name
            f.save(path)
            rel = f"uploads/properties/{name}"
            property_model.add_image(property_id, rel, is_primary=(i == 0))
            if i == 0:
                execute(
                    "UPDATE properties SET image_url = %s WHERE id = %s",
                    (rel, property_id),
                )
