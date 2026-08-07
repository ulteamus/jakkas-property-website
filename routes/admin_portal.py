from functools import wraps
from datetime import date, timedelta

from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from config import ALLOWED_DOC, ALLOWED_IMAGE, ALLOWED_VIDEO, LEAD_STATUSES, PROPERTY_TYPES
from database import execute, query_all, query_one
from models import activity_log as activity_model
from models import analytics as analytics_model
from models import customer_visit as visit_model
from models import inquiry as inquiry_model
from models import lead as lead_model
from models import property as prop_model
from models import reviews as reviews_model
from models import submission as submission_model
from models.admin import (
    PERMISSION_KEYS,
    ROLE_BROKER,
    ROLE_CALLER,
    ROLE_KEYS,
    ROLE_MANAGER,
    ROLE_PRESETS,
    Admin,
    role_options_for_ui,
)
from services import follow_up
from utils.pdf_export import (
    build_simple_pdf,
    generate_leads_list_pdf,
    generate_single_lead_pdf,
)
from utils.helpers import save_upload

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _owner_scope_admin_id():
    """Brokers (and other non-manager employees) only see their own listings.

    super_admin / main_admin / manager see all properties.
    """
    if getattr(current_user, "is_super_admin", False):
        return None
    role = getattr(current_user, "role", None)
    if role == ROLE_MANAGER:
        return None
    if role == ROLE_BROKER:
        return current_user.id
    # Keep existing isolation for executives/callers creating listings.
    return current_user.id


def admin_required(f):
    @wraps(f)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_active:
            return redirect(url_for("auth.admin_login"))
        if not getattr(current_user, "is_admin", False):
            abort(403)
        has_permission = getattr(current_user, "has_permission", None)
        if not callable(has_permission):
            abort(403)
        if not current_user.is_super_admin and not any(has_permission(key) for key in PERMISSION_KEYS):
            abort(403)
        return f(*args, **kwargs)

    return wrapped


def permission_required(permission_key):
    def decorator(f):
        @wraps(f)
        @admin_required
        def wrapped(*args, **kwargs):
            if not current_user.has_permission(permission_key):
                abort(403)
            return f(*args, **kwargs)

        return wrapped

    return decorator


def super_admin_required(f):
    @wraps(f)
    @admin_required
    def wrapped(*args, **kwargs):
        if not current_user.is_super_admin:
            abort(403)
        return f(*args, **kwargs)

    return wrapped


def _ensure_property_owner(prop):
    if not prop:
        abort(404)
    if getattr(current_user, "is_super_admin", False):
        return
    if getattr(current_user, "role", None) == ROLE_MANAGER:
        return
    if getattr(current_user, "role", None) == ROLE_BROKER:
        if int(prop.get("owner_admin_id") or 0) != int(current_user.id):
            abort(403)
        return
    # Non-broker employees remain scoped to own listings.
    if int(prop.get("owner_admin_id") or 0) != int(current_user.id):
        abort(403)


def _inquiry_owner_scope():
    if getattr(current_user, "role", None) == ROLE_BROKER:
        return current_user.id
    return None


def _ensure_inquiry_owner(inquiry):
    if not inquiry:
        abort(404)
    if getattr(current_user, "role", None) != ROLE_BROKER:
        return
    owner_id = inquiry.get("property_owner_admin_id")
    if owner_id is None and inquiry.get("property_id"):
        prop = prop_model.get_by_id(inquiry.get("property_id"))
        owner_id = (prop or {}).get("owner_admin_id")
    if int(owner_id or 0) != int(current_user.id):
        abort(403)


def _ensure_lead_owner(lead):
    if not lead:
        abort(404)
    if getattr(current_user, "role", None) != ROLE_BROKER:
        return
    owner_id = lead.get("property_owner_admin_id")
    if owner_id is None and lead.get("property_id"):
        prop = prop_model.get_by_id(lead.get("property_id"))
        owner_id = (prop or {}).get("owner_admin_id")
    if int(owner_id or 0) != int(current_user.id):
        abort(403)


def _allowed_caller_status(status_value):
    return (status_value or "").strip().lower() in {"contacted", "interested", "site_visit_scheduled"}


def _log_admin_action(action_key, action_label, entity_type=None, entity_id=None, meta=None):
    try:
        activity_model.log_action(
            current_user.id if getattr(current_user, "is_authenticated", False) else None,
            action_key=action_key,
            action_label=action_label,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=meta or {},
        )
    except Exception:
        pass


def _coerce_iso_date(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        return None


def _resolve_inquiry_window(range_filter, start_date_raw=None, end_date_raw=None):
    today = date.today()
    range_key = (range_filter or "week").strip().lower()
    if range_key == "day":
        start = today
        end = today
    elif range_key == "custom":
        start_value = _coerce_iso_date(start_date_raw)
        end_value = _coerce_iso_date(end_date_raw)
        if not start_value and not end_value:
            start = today - timedelta(days=6)
            end = today
            range_key = "week"
        else:
            start = date.fromisoformat(start_value or end_value)
            end = date.fromisoformat(end_value or start_value)
    else:
        start = today - timedelta(days=6)
        end = today
        range_key = "week"
    if start > end:
        start, end = end, start
    return range_key, start.isoformat(), end.isoformat()


def _pdf_download(filename, title, lines):
    payload = build_simple_pdf(title, lines)
    return _pdf_bytes_download(filename, payload)


def _pdf_bytes_download(filename, payload):
    response = make_response(payload)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _build_mock_clause(columns):
    keywords = ["test", "demo", "mock", "dummy", "sample"]
    parts = []
    params = []
    for column in columns:
        for keyword in keywords:
            parts.append(f"LOWER(IFNULL({column},'')) LIKE %s")
            params.append(f"%{keyword}%")
    return "(" + " OR ".join(parts) + ")", params


def _count_with_clause(table_name, clause, params):
    try:
        row = query_one(f"SELECT COUNT(*) AS c FROM {table_name} WHERE {clause}", tuple(params))
        return int((row or {}).get("c") or 0)
    except Exception:
        return 0


def _delete_with_clause(table_name, clause, params):
    try:
        execute(f"DELETE FROM {table_name} WHERE {clause}", tuple(params))
    except Exception:
        return


def _mock_counts():
    targets = {
        "properties": ["property_name", "slug", "area_name", "address", "description"],
        "inquiries": ["name", "mobile", "email", "message", "source", "notes"],
        "owner_submissions": ["owner_name", "owner_mobile", "owner_email", "property_title", "property_address"],
        "leads": ["name", "mobile", "email", "preferred_area"],
        "visitor_events": ["visitor_id", "event_type", "meta"],
        "activity_logs": ["action_key", "action_label", "meta_json"],
    }
    snapshot = {}
    for table_name, columns in targets.items():
        clause, params = _build_mock_clause(columns)
        snapshot[table_name] = _count_with_clause(table_name, clause, params)
    return snapshot


def _flush_mock_rows():
    targets = {
        "properties": ["property_name", "slug", "area_name", "address", "description"],
        "inquiries": ["name", "mobile", "email", "message", "source", "notes"],
        "owner_submissions": ["owner_name", "owner_mobile", "owner_email", "property_title", "property_address"],
        "leads": ["name", "mobile", "email", "preferred_area"],
        "visitor_events": ["visitor_id", "event_type", "meta"],
        "activity_logs": ["action_key", "action_label", "meta_json"],
    }
    removed = {}
    for table_name, columns in targets.items():
        clause, params = _build_mock_clause(columns)
        count = _count_with_clause(table_name, clause, params)
        if count > 0:
            _delete_with_clause(table_name, clause, params)
        removed[table_name] = count
    return removed


@admin_bp.route("/")
@admin_required
def dashboard():
    follow_up.check_follow_ups()
    stats = analytics_model.dashboard_stats()
    stats.update(lead_model.stats())
    stats["conversion_rate"] = analytics_model.conversion_rate()
    stats["pending_submissions"] = submission_model.count_by_status(
        "pending", owner_admin_id=_owner_scope_admin_id()
    )
    recent_inquiries = inquiry_model.get_all(
        limit=8, owner_admin_id=_inquiry_owner_scope()
    )
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_inquiries=recent_inquiries,
        trending=analytics_model.trending_areas(5),
        top_properties=analytics_model.most_viewed_properties(5),
    )


@admin_bp.route("/properties")
@permission_required("manage_properties")
def properties():
    status = request.args.get("status") or None
    props = prop_model.to_dict_list(
        prop_model.search(
            status=status or "available",
            limit=500,
            all_statuses=(status is None),
            owner_admin_id=_owner_scope_admin_id(),
        ),
        public=False,
    )
    submission_map = submission_model.latest_for_property_ids(
        [prop.get("id") for prop in props if prop.get("status") == "reserved"],
        status="pending",
    )
    return render_template(
        "admin/properties.html",
        properties=props,
        statuses=["available", "sold", "rented", "reserved"],
        selected_status=status or "all",
        submission_map=submission_map,
    )


@admin_bp.route("/properties/add", methods=["GET", "POST"])
@admin_bp.route("/properties/<int:pid>/edit", methods=["GET", "POST"])
@permission_required("manage_properties")
def property_form(pid=None):
    prop = prop_model.get_by_id(pid) if pid else None
    if prop:
        _ensure_property_owner(prop)
        prop = prop_model.to_dict(prop, public=False)

    if request.method == "POST":
        try:
            data = _form_property(request.form)
        except ValueError as exc:
            flash(str(exc), "danger")
            areas = prop_model.areas_list()
            return render_template("admin/property_form.html", property=prop, types=PROPERTY_TYPES, areas=areas)
        previous_status = (prop or {}).get("status")
        duplicate = prop_model.find_duplicate(
            data.get("property_name"),
            data.get("address"),
            data.get("area_name"),
            exclude_id=pid,
        )
        if duplicate:
            flash("A property with same name and address already exists.", "warning")
            return redirect(url_for("admin.property_form", pid=pid) if pid else url_for("admin.property_form"))
        if pid:
            prop_model.update(pid, data)
            _upload_media(request, pid)
            _log_admin_action(
                "property_updated",
                "Updated property",
                entity_type="property",
                entity_id=pid,
                meta={"property_name": data.get("property_name")},
            )
            if previous_status != data.get("status"):
                _log_admin_action(
                    "property_status_changed",
                    "Changed property status",
                    entity_type="property",
                    entity_id=pid,
                    meta={
                        "from_status": previous_status,
                        "to_status": data.get("status"),
                        "property_name": data.get("property_name"),
                    },
                )
            flash("Property updated.", "success")
        else:
            created = prop_model.create(data, created_by_admin_id=current_user.id)
            _upload_media(request, created["id"])
            _log_admin_action(
                "property_added",
                "Added property",
                entity_type="property",
                entity_id=created["id"],
                meta={
                    "property_name": created.get("property_name"),
                    "creation_source": created.get("creation_source"),
                },
            )
            flash("Property added.", "success")
        return redirect(url_for("admin.properties"))
    areas = prop_model.areas_list()
    return render_template("admin/property_form.html", property=prop, types=PROPERTY_TYPES, areas=areas)


@admin_bp.route("/properties/<int:pid>/delete", methods=["POST"])
@permission_required("manage_properties")
def delete_property(pid):
    prop = prop_model.get_by_id(pid)
    _ensure_property_owner(prop)
    confirm_text = (request.form.get("confirm_text") or "").strip().upper()
    confirm_property_id = str(request.form.get("confirm_property_id") or "").strip()
    if confirm_text != "DELETE" or confirm_property_id != str(pid):
        flash("Delete confirmation mismatch. Property was not deleted.", "warning")
        return redirect(url_for("admin.properties"))
    prop_model.delete(pid)
    _log_admin_action(
        "property_deleted",
        "Deleted property",
        entity_type="property",
        entity_id=pid,
        meta={"property_name": prop.get("property_name") if prop else None},
    )
    flash("Property deleted.", "info")
    return redirect(url_for("admin.properties"))


@admin_bp.route("/leads")
@permission_required("manage_leads")
def leads():
    status = request.args.get("status")
    tier = request.args.get("tier")
    return render_template(
        "admin/leads.html",
        leads=lead_model.get_all(
            status=status, tier=tier, owner_admin_id=_inquiry_owner_scope()
        ),
        statuses=LEAD_STATUSES,
    )


@admin_bp.route("/leads/export-pdf")
@permission_required("manage_leads")
def leads_export_pdf():
    status = request.args.get("status")
    tier = request.args.get("tier")
    urgent_only = (request.args.get("urgent") or "").strip().lower() in {"1", "true", "yes"}
    rows = lead_model.get_all(
        status=status,
        tier=tier,
        urgent_only=urgent_only,
        limit=1000,
        owner_admin_id=_inquiry_owner_scope(),
    )
    payload = generate_leads_list_pdf(
        rows,
        current_user,
        filters={"status": status, "tier": tier, "urgent_only": urgent_only or None},
    )
    stamp = date.today().isoformat().replace("-", "")
    _log_admin_action(
        "leads_pdf_exported",
        "Downloaded leads PDF report",
        entity_type="lead",
        meta={"count": len(rows), "status": status or "all", "tier": tier or "all"},
    )
    return _pdf_bytes_download(f"leads-export-{stamp}.pdf", payload)


@admin_bp.route("/leads/<int:lid>")
@permission_required("manage_leads")
def lead_detail(lid):
    lead = lead_model.get_by_id(lid, owner_admin_id=_inquiry_owner_scope())
    if not lead:
        abort(404)
    _ensure_lead_owner(lead)
    return render_template("admin/lead_detail.html", lead=lead, notes=lead_model.get_notes(lid), statuses=LEAD_STATUSES)


@admin_bp.route("/leads/<int:lid>/export-pdf")
@permission_required("manage_leads")
def lead_export_pdf(lid):
    lead = lead_model.get_by_id(lid, owner_admin_id=_inquiry_owner_scope())
    if not lead:
        abort(404)
    _ensure_lead_owner(lead)
    notes = lead_model.get_notes(lid)
    inquiries = inquiry_model.get_for_lead(lead)
    payload = generate_single_lead_pdf(lead, inquiries, notes, current_user)
    _log_admin_action(
        "lead_dossier_pdf_exported",
        "Downloaded lead dossier PDF",
        entity_type="lead",
        entity_id=lid,
        meta={"name": lead.get("name")},
    )
    return _pdf_bytes_download(f"lead-dossier-{lid}.pdf", payload)


@admin_bp.route("/leads/<int:lid>/update", methods=["POST"])
@permission_required("manage_leads")
def update_lead(lid):
    lead = lead_model.get_by_id(lid, owner_admin_id=_inquiry_owner_scope())
    _ensure_lead_owner(lead)
    new_status = request.form.get("status")
    if current_user.role == ROLE_CALLER and not _allowed_caller_status(new_status):
        flash("Caller role can only update follow-up statuses.", "warning")
        return redirect(url_for("admin.lead_detail", lid=lid))

    lead_model.update_status(lid, new_status)
    note = request.form.get("note")
    if note:
        lead_model.add_note(lid, note, current_user.id, request.form.get("follow_up_date") or None)
    lead_model.refresh_score(lid)
    flash("Lead updated.", "success")
    return redirect(url_for("admin.lead_detail", lid=lid))


@admin_bp.route("/inquiries")
@permission_required("manage_inquiries")
def inquiries():
    selected_range = request.args.get("range", "week")
    selected_status = (request.args.get("status") or "").strip().lower()
    selected_type = (request.args.get("inquiry_type") or "all").strip().lower()
    range_key, start_date, end_date = _resolve_inquiry_window(
        selected_range,
        request.args.get("start_date"),
        request.args.get("end_date"),
    )
    if selected_status not in inquiry_model.INQUIRY_STATUSES:
        selected_status = ""
    if selected_type not in {"all", "site_visit", "general", "property"}:
        selected_type = "all"
    rows = inquiry_model.get_all(
        limit=500,
        start_date=start_date,
        end_date=end_date,
        status=selected_status or None,
        owner_admin_id=_inquiry_owner_scope(),
        inquiry_type=None if selected_type == "all" else selected_type,
    )
    _log_admin_action(
        "sensitive_inquiries_viewed",
        "Viewed inquiries with sensitive contact data",
        entity_type="inquiry",
        meta={
            "count": len(rows),
            "range": range_key,
            "status": selected_status or "all",
            "inquiry_type": selected_type,
        },
    )
    return render_template(
        "admin/inquiries.html",
        inquiries=rows,
        statuses=inquiry_model.INQUIRY_STATUSES,
        selected_status=selected_status or "all",
        selected_inquiry_type=selected_type,
        inquiry_types=[
            ("all", "All"),
            ("site_visit", "Site Visit Requests"),
            ("general", "General Inquiries"),
            ("property", "Property-Specific Inquiries"),
        ],
        range_filter=range_key,
        start_date=start_date,
        end_date=end_date,
    )


@admin_bp.route("/inquiries/<int:inquiry_id>/detail")
@permission_required("manage_inquiries")
def inquiry_detail(inquiry_id):
    inquiry = inquiry_model.get_by_id(inquiry_id, owner_admin_id=_inquiry_owner_scope())
    if not inquiry:
        abort(404)
    _ensure_inquiry_owner(inquiry)
    _log_admin_action(
        "sensitive_inquiry_detail_view",
        "Viewed sensitive inquiry details",
        entity_type="inquiry",
        entity_id=inquiry_id,
        meta={"name": inquiry.get("name"), "mobile": inquiry.get("mobile")},
    )
    return render_template(
        "admin/inquiry_detail.html",
        inquiry=inquiry,
        statuses=inquiry_model.INQUIRY_STATUSES,
    )


@admin_bp.route("/inquiries/<int:inquiry_id>/update", methods=["POST"])
@permission_required("manage_inquiries")
def update_inquiry(inquiry_id):
    inquiry = inquiry_model.get_by_id(inquiry_id, owner_admin_id=_inquiry_owner_scope())
    if not inquiry:
        abort(404)
    _ensure_inquiry_owner(inquiry)
    updated = inquiry_model.update_entry(
        inquiry_id,
        status=request.form.get("status"),
        notes=request.form.get("notes"),
    )
    _log_admin_action(
        "inquiry_updated",
        "Updated inquiry status/notes",
        entity_type="inquiry",
        entity_id=inquiry_id,
        meta={
            "from_status": inquiry.get("status"),
            "to_status": (updated or {}).get("status"),
        },
    )
    flash("Inquiry updated.", "success")
    return redirect(request.referrer or url_for("admin.inquiries"))


@admin_bp.route("/inquiries/<int:inquiry_id>/delete", methods=["POST"])
@permission_required("manage_inquiries")
def delete_inquiry(inquiry_id):
    inquiry = inquiry_model.get_by_id(inquiry_id, owner_admin_id=_inquiry_owner_scope())
    if not inquiry:
        abort(404)
    _ensure_inquiry_owner(inquiry)
    inquiry_model.delete(inquiry_id)
    _log_admin_action(
        "inquiry_deleted",
        "Deleted inquiry",
        entity_type="inquiry",
        entity_id=inquiry_id,
        meta={"name": inquiry.get("name"), "mobile": inquiry.get("mobile")},
    )
    flash("Inquiry deleted.", "warning")
    return redirect(request.referrer or url_for("admin.inquiries"))


@admin_bp.route("/inquiries/bulk-delete", methods=["POST"])
@permission_required("manage_inquiries")
def bulk_delete_inquiries():
    ids = request.form.getlist("inquiry_ids")
    deleted = inquiry_model.delete_many(ids)
    _log_admin_action(
        "inquiry_bulk_deleted",
        "Bulk deleted inquiries",
        entity_type="inquiry",
        meta={"count": deleted},
    )
    flash(f"Deleted {deleted} inquir{'y' if deleted == 1 else 'ies'}.", "warning")
    return redirect(request.referrer or url_for("admin.inquiries"))


@admin_bp.route("/inquiries/print")
@permission_required("manage_inquiries")
def print_inquiries():
    selected_range = request.args.get("range", "week")
    selected_status = (request.args.get("status") or "").strip().lower()
    selected_type = (request.args.get("inquiry_type") or "all").strip().lower()
    range_key, start_date, end_date = _resolve_inquiry_window(
        selected_range,
        request.args.get("start_date"),
        request.args.get("end_date"),
    )
    if selected_status not in inquiry_model.INQUIRY_STATUSES:
        selected_status = ""
    if selected_type not in {"all", "site_visit", "general", "property"}:
        selected_type = "all"
    rows = inquiry_model.get_all(
        limit=1000,
        start_date=start_date,
        end_date=end_date,
        status=selected_status or None,
        owner_admin_id=_inquiry_owner_scope(),
        inquiry_type=None if selected_type == "all" else selected_type,
    )
    return render_template(
        "admin/inquiries_print.html",
        inquiries=rows,
        statuses=inquiry_model.INQUIRY_STATUSES,
        selected_status=selected_status or "all",
        selected_inquiry_type=selected_type,
        range_filter=range_key,
        start_date=start_date,
        end_date=end_date,
    )


def _resolve_submission_period(period_filter):
    today = date.today()
    key = (period_filter or "weekly").strip().lower()
    if key in {"daily", "day"}:
        return "daily", today.isoformat(), today.isoformat()
    if key in {"monthly", "month"}:
        return "monthly", today.replace(day=1).isoformat(), today.isoformat()
    if key in {"yearly", "year"}:
        return "yearly", today.replace(month=1, day=1).isoformat(), today.isoformat()
    return "weekly", (today - timedelta(days=6)).isoformat(), today.isoformat()


def _submission_redirect_args():
    status = (request.form.get("redirect_status") or request.args.get("status") or "pending").strip().lower()
    period = (request.form.get("redirect_period") or request.args.get("period") or "weekly").strip().lower()
    area = (request.form.get("redirect_area") or request.args.get("area") or "").strip()
    seller_type = (request.form.get("redirect_seller_type") or request.args.get("seller_type") or "").strip().lower()
    if status not in {"pending", "approved", "rejected", "all"}:
        status = "pending"
    if period not in {"daily", "weekly", "monthly", "yearly"}:
        period = "weekly"
    if seller_type not in {"owner", "broker", "developer"}:
        seller_type = ""
    args = {"status": status, "period": period}
    if area:
        args["area"] = area
    if seller_type:
        args["seller_type"] = seller_type
    return args


SELL_AREA_FILTER_OPTIONS = [
    "Adajan",
    "Vesu",
    "Pal",
    "Piplod",
    "Athwa",
    "City Light",
    "Althan",
    "Varachha",
    "Katargam",
    "Ring Road",
]


def _media_paths_from_submission(submission, key):
    """Normalize images/videos JSON entries to file path strings."""
    paths = []
    for item in submission.get(key) or []:
        if isinstance(item, str) and item.strip():
            paths.append(item.strip())
        elif isinstance(item, dict):
            path = (item.get("file_path") or item.get("path") or item.get("filename") or "").strip()
            if path:
                paths.append(path)
    return paths


def _copy_submission_media_to_property(submission, property_id):
    """Copy submission media filenames onto properties (idempotent; no deletes)."""
    if not property_id:
        return
    media = prop_model.get_media(property_id) or {}
    existing_imgs = {
        (row.get("file_path") or "").strip()
        for row in (media.get("images") or [])
        if row.get("file_path")
    }
    existing_vids = {
        (row.get("file_path") or "").strip()
        for row in (media.get("videos") or [])
        if row.get("file_path")
    }
    images = _media_paths_from_submission(submission, "images")
    videos = _media_paths_from_submission(submission, "videos")
    for i, path in enumerate(images):
        if path in existing_imgs:
            continue
        prop_model.add_image(
            property_id,
            path,
            is_primary=(not existing_imgs and i == 0),
            sort_order=len(existing_imgs) + i,
        )
        existing_imgs.add(path)
    for i, path in enumerate(videos):
        if path in existing_vids:
            continue
        prop_model.add_video(property_id, path, sort_order=len(existing_vids) + i)
        existing_vids.add(path)


def _create_property_from_submission(submission):
    """Create a public listing from a sell submission (status=available)."""
    listing_intent = (submission.get("listing_intent") or "sell").lower()
    listing_type = "rent" if listing_intent == "rent" else "sale"
    created = prop_model.create(
        {
            "property_name": submission.get("property_title") or "Untitled Property",
            "property_type": submission.get("property_type") or "flat",
            "area_name": submission.get("location_area") or submission.get("city") or "Surat",
            "address": submission.get("property_address"),
            "price": float(submission.get("price") or 0),
            "bhk": int(submission.get("bhk") or 0),
            "sq_ft": float(submission.get("area_sq_ft") or 1),
            "description": submission.get("description"),
            "amenities": submission.get("amenities") or [],
            "status": "available",
            "is_featured": False,
            "listing_type": listing_type,
            "listing_intent": "rent" if listing_intent == "rent" else "sell",
            "seller_type": submission.get("seller_type") or submission.get("submitter_type"),
            "block_wing": submission.get("block_wing"),
            "unit_number": submission.get("unit_number")
            or submission.get("apartment_number")
            or submission.get("bungalow_number"),
            "creation_source": "user_submission",
            "primary_image": (_media_paths_from_submission(submission, "images") or [None])[0],
        },
        created_by_admin_id=submission.get("owner_admin_id") or current_user.id,
    )
    property_id = created["id"]
    submission_model.link_property(submission["id"], property_id)
    submission["property_id"] = property_id
    _copy_submission_media_to_property(submission, property_id)
    return property_id


def _ensure_submission_property_published(submission):
    """
    Guarantee an approved submission has a live property row with status=available.
    Heals orphan property_id links (ID set but row missing) so listings appear publicly.
    Returns True when a create or status publish occurred.
    """
    property_id = submission.get("property_id")
    existing_prop = prop_model.get_by_id(property_id) if property_id else None
    changed = False
    if not existing_prop:
        property_id = _create_property_from_submission(submission)
        existing_prop = prop_model.get_by_id(property_id)
        changed = True
        previous_prop_status = None
    else:
        previous_prop_status = (existing_prop or {}).get("status")

    if property_id and previous_prop_status != "available":
        prop_model.set_status(property_id, "available")
        changed = True
        _log_admin_action(
            "property_status_changed",
            "Changed property status",
            entity_type="property",
            entity_id=property_id,
            meta={"from_status": previous_prop_status, "to_status": "available"},
        )
    if property_id:
        _copy_submission_media_to_property(submission, property_id)
        _ensure_submission_lead(submission)
    return changed


def _apply_submission_status_change(submission, new_status, review_note=None):
    sid = submission["id"]
    previous = (submission.get("status") or "").lower()
    clean_status = (new_status or "").strip().lower()
    if clean_status not in {"pending", "approved", "rejected"}:
        raise ValueError("Invalid submission status.")
    # Re-approve must still publish orphan/missing properties to the public panel.
    if previous == clean_status:
        if clean_status == "approved":
            return _ensure_submission_property_published(submission)
        return False

    # Permanent persistence: never delete owner_submissions on approve/reject.
    submission_model.set_submission_status(
        sid,
        clean_status,
        reviewed_by=current_user.id,
        review_note=review_note,
    )
    property_id = submission.get("property_id")

    if clean_status == "approved":
        _ensure_submission_property_published(submission)
        property_id = submission.get("property_id")
    elif property_id:
        existing_prop = prop_model.get_by_id(property_id)
        previous_prop_status = (existing_prop or {}).get("status")
        if existing_prop:
            prop_model.set_status(property_id, "reserved")
            if previous_prop_status != "reserved":
                _log_admin_action(
                    "property_status_changed",
                    "Changed property status",
                    entity_type="property",
                    entity_id=property_id,
                    meta={"from_status": previous_prop_status, "to_status": "reserved"},
                )

    action_key = {
        "approved": "submission_approved",
        "rejected": "submission_rejected",
        "pending": "submission_pending",
    }[clean_status]
    _log_admin_action(
        action_key,
        f"Set sell property submission to {clean_status}",
        entity_type="submission",
        entity_id=sid,
        meta={"property_id": property_id, "from_status": previous, "to_status": clean_status},
    )
    return True


@admin_bp.route("/sell-properties")
@permission_required("manage_submissions")
def sell_properties():
    status_filter = (request.args.get("status") or "pending").strip().lower()
    allowed = {"pending", "approved", "rejected", "all"}
    if status_filter not in allowed:
        status_filter = "pending"
    area_filter = (request.args.get("area") or "").strip()
    seller_type_filter = (request.args.get("seller_type") or "").strip().lower()
    if seller_type_filter not in {"owner", "broker", "developer"}:
        seller_type_filter = ""
    period_key, start_date, end_date = _resolve_submission_period(request.args.get("period"))
    owner_scope = _owner_scope_admin_id()
    submissions_rows = submission_model.list_submissions(
        status=None if status_filter == "all" else status_filter,
        limit=500,
        owner_admin_id=owner_scope,
        start_date=start_date,
        end_date=end_date,
        area=area_filter or None,
        seller_type=seller_type_filter or None,
    )
    period_stats = submission_model.period_counts(owner_admin_id=owner_scope)
    return render_template(
        "admin/sell_properties.html",
        submissions=submissions_rows,
        status_filter=status_filter,
        period_filter=period_key,
        area_filter=area_filter,
        seller_type_filter=seller_type_filter,
        area_options=SELL_AREA_FILTER_OPTIONS,
        period_stats=period_stats,
        statuses=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("all", "All"),
        ],
        periods=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
    )


@admin_bp.route("/submissions")
@permission_required("manage_submissions")
def submissions_redirect():
    return redirect(url_for("admin.sell_properties", **request.args))


@admin_bp.route("/sell-properties/<int:sid>/update", methods=["POST"])
@permission_required("manage_submissions")
def update_sell_property(sid):
    submission = submission_model.get_submission(sid, owner_admin_id=_owner_scope_admin_id())
    if not submission:
        abort(404)
    new_status = (request.form.get("status") or "").strip().lower()
    review_note = request.form.get("review_note")
    try:
        changed = _apply_submission_status_change(submission, new_status, review_note=review_note)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("admin.sell_properties", **_submission_redirect_args()))
    if changed:
        labels = {"approved": "approved and published", "rejected": "rejected", "pending": "set to pending"}
        flash(f"Sell property submission {labels.get(new_status, 'updated')}.", "success")
    else:
        flash("No status change was needed.", "info")
    return redirect(url_for("admin.sell_properties", **_submission_redirect_args()))


@admin_bp.route("/sell-properties/<int:sid>/edit", methods=["GET", "POST"])
@permission_required("manage_submissions")
def edit_sell_property(sid):
    submission = submission_model.get_submission(sid, owner_admin_id=_owner_scope_admin_id())
    if not submission:
        abort(404)
    if request.method == "POST":
        required = [
            "owner_name", "owner_mobile", "owner_address",
            "property_title", "property_type", "property_address",
        ]
        missing = [field for field in required if not request.form.get(field)]
        if missing:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("admin.edit_sell_property", sid=sid))
        amenities = request.form.getlist("amenities")
        payload = {
            "owner_name": request.form.get("owner_name"),
            "owner_mobile": request.form.get("owner_mobile"),
            "owner_alt_mobile": request.form.get("owner_alt_mobile"),
            "owner_email": request.form.get("owner_email"),
            "owner_address": request.form.get("owner_address"),
            "property_title": request.form.get("property_title"),
            "property_type": request.form.get("property_type"),
            "property_status": request.form.get("property_status") or "sell",
            "bhk": int(request.form.get("bhk") or 0),
            "bungalow_number": request.form.get("bungalow_number"),
            "area_sq_ft": float(str(request.form.get("area_sq_ft") or 0).replace(",", "")),
            "price": float(str(request.form.get("price") or 0).replace(",", "")),
            "property_address": request.form.get("property_address"),
            "city": request.form.get("city") or "Surat",
            "location_area": request.form.get("location_area"),
            "description": request.form.get("description"),
            "amenities": amenities,
            "listing_intent": request.form.get("listing_intent") or "buy",
            "review_note": request.form.get("review_note"),
        }
        submission_model.update_submission(sid, payload)
        property_id = submission.get("property_id")
        if property_id:
            prop_type = (payload["property_type"] or "flat").lower()
            if prop_type == "commercial":
                prop_type = "shop"
            elif prop_type == "apartment":
                prop_type = "flat"
            elif prop_type == "villa":
                prop_type = "bungalow"
            prop_model.update(
                property_id,
                {
                    "property_name": payload["property_title"],
                    "property_type": prop_type,
                    "area_name": payload.get("location_area") or payload.get("city") or "Surat",
                    "address": payload["property_address"],
                    "price": payload["price"],
                    "bhk": payload["bhk"],
                    "sq_ft": payload["area_sq_ft"],
                    "description": payload.get("description"),
                    "amenities": amenities,
                    "status": "available" if submission.get("status") == "approved" else "reserved",
                    "listing_type": "sale",
                },
            )
        _log_admin_action(
            "submission_updated",
            "Updated sell property submission",
            entity_type="submission",
            entity_id=sid,
            meta={"property_id": property_id},
        )
        flash("Sell property submission updated.", "success")
        return redirect(url_for("admin.sell_properties", **_submission_redirect_args()))
    return render_template("admin/sell_property_edit.html", submission=submission)


@admin_bp.route("/sell-properties/<int:sid>/delete", methods=["POST"])
@permission_required("manage_submissions")
def delete_sell_property(sid):
    submission = submission_model.get_submission(sid, owner_admin_id=_owner_scope_admin_id())
    if not submission:
        abort(404)
    property_id = submission.get("property_id")
    if property_id:
        prop = prop_model.get_by_id(property_id)
        if prop and prop.get("creation_source") == "user_submission":
            prop_model.delete(property_id)
    submission_model.delete_submission(sid)
    _log_admin_action(
        "submission_deleted",
        "Deleted sell property submission",
        entity_type="submission",
        entity_id=sid,
        meta={"property_id": property_id},
    )
    flash("Sell property submission deleted.", "warning")
    return redirect(url_for("admin.sell_properties", **_submission_redirect_args()))


@admin_bp.route("/sell-properties/print")
@permission_required("manage_submissions")
def print_sell_properties():
    status_filter = (request.args.get("status") or "all").strip().lower()
    if status_filter not in {"pending", "approved", "rejected", "all"}:
        status_filter = "all"
    area_filter = (request.args.get("area") or "").strip()
    seller_type_filter = (request.args.get("seller_type") or "").strip().lower()
    if seller_type_filter not in {"owner", "broker", "developer"}:
        seller_type_filter = ""
    period_key, start_date, end_date = _resolve_submission_period(request.args.get("period"))
    rows = submission_model.list_submissions(
        status=None if status_filter == "all" else status_filter,
        limit=1000,
        owner_admin_id=_owner_scope_admin_id(),
        start_date=start_date,
        end_date=end_date,
        area=area_filter or None,
        seller_type=seller_type_filter or None,
    )
    return render_template(
        "admin/sell_properties_print.html",
        submissions=rows,
        status_filter=status_filter,
        period_filter=period_key,
        area_filter=area_filter,
        seller_type_filter=seller_type_filter,
        start_date=start_date,
        end_date=end_date,
    )


@admin_bp.route("/submissions/<int:sid>/approve", methods=["POST"])
@admin_bp.route("/sell-properties/<int:sid>/approve", methods=["POST"])
@permission_required("manage_submissions")
def approve_submission(sid):
    submission = submission_model.get_submission(sid, owner_admin_id=_owner_scope_admin_id())
    if not submission:
        abort(404)
    # Always run status change: re-approve heals missing/orphan properties so they
    # surface on the public listings panel (status=available).
    changed = _apply_submission_status_change(
        submission,
        "approved",
        review_note=request.form.get("review_note"),
    )
    if changed:
        flash("Submission approved and property published.", "success")
    else:
        flash("Submission is already approved.", "info")
    return redirect(url_for("admin.sell_properties", **_submission_redirect_args()))


@admin_bp.route("/submissions/<int:sid>/reject", methods=["POST"])
@admin_bp.route("/sell-properties/<int:sid>/reject", methods=["POST"])
@permission_required("manage_submissions")
def reject_submission(sid):
    submission = submission_model.get_submission(sid, owner_admin_id=_owner_scope_admin_id())
    if not submission:
        abort(404)
    if submission.get("status") != "rejected":
        _apply_submission_status_change(
            submission,
            "rejected",
            review_note=request.form.get("review_note"),
        )
        flash("Submission rejected.", "warning")
    else:
        flash("Submission is already rejected.", "info")
    return redirect(url_for("admin.sell_properties", **_submission_redirect_args()))


@admin_bp.route("/reviews")
@permission_required("manage_reviews")
def reviews():
    return render_template(
        "admin/reviews.html",
        reviews=reviews_model.list_reviews(include_inactive=True, limit=500),
    )


@admin_bp.route("/reviews/add", methods=["POST"])
@permission_required("manage_reviews")
def add_review():
    reviews_model.create_review(
        name=request.form.get("client_name"),
        location=request.form.get("client_location"),
        text=request.form.get("review_text"),
        rating=request.form.get("rating", 5),
        is_active=(request.form.get("is_active") == "on"),
    )
    flash("Review added successfully.", "success")
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/reviews/<int:review_id>/edit", methods=["POST"])
@permission_required("manage_reviews")
def edit_review(review_id):
    existing = reviews_model.get_review(review_id)
    if not existing:
        abort(404)
    reviews_model.update_review(
        review_id=review_id,
        name=request.form.get("client_name"),
        location=request.form.get("client_location"),
        text=request.form.get("review_text"),
        rating=request.form.get("rating", 5),
        is_active=(request.form.get("is_active", "1") in {"1", "true", "on"}),
    )
    flash("Review updated.", "success")
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
@permission_required("manage_reviews")
def delete_review(review_id):
    reviews_model.delete_review(review_id)
    flash("Review deleted.", "info")
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/reviews/<int:review_id>/toggle", methods=["POST"])
@permission_required("manage_reviews")
def toggle_review(review_id):
    is_active = request.form.get("is_active", "0") in {"1", "true", "on"}
    reviews_model.set_review_active(review_id, is_active)
    flash("Review status updated.", "success")
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/reviews/comments/<int:comment_id>/delete", methods=["POST"])
@permission_required("manage_reviews")
def delete_review_comment(comment_id):
    reviews_model.delete_comment(comment_id)
    flash("Comment deleted.", "info")
    return redirect(url_for("admin.reviews"))


@admin_bp.route("/analytics")
@permission_required("view_analytics")
def analytics():
    return render_template(
        "admin/analytics.html",
        trending=analytics_model.trending_areas(12),
        by_type=analytics_model.demand_by_type(),
        top=analytics_model.most_viewed_properties(15),
        conversion=analytics_model.conversion_rate(),
    )


@admin_bp.route("/price-predictor", methods=["GET", "POST"])
@permission_required("manage_settings")
def price_predictor_page():
    flash("Price AI is no longer available. Use the public Chatbot instead.", "info")
    return redirect(url_for("public.chatbot"))


def _parse_bool_form(form, key):
    return str(form.get(key, "")).strip().lower() in {"1", "true", "yes", "on"}


def _permissions_from_form(form):
    requested = form.getlist("permissions")
    return [perm for perm in requested if perm in PERMISSION_KEYS]


@admin_bp.route("/employees")
@super_admin_required
def admin_users():
    admins = Admin.list_admins(include_inactive=True)
    edit_id = request.args.get("edit", type=int)
    setup_admin_id = request.args.get("setup_admin", type=int)
    setup_payload = None
    if setup_admin_id:
        setup_payload = Admin.totp_setup_payload(Admin.get_by_id(setup_admin_id, include_inactive=True))
    role_keys = list(ROLE_KEYS)
    if ROLE_BROKER not in role_keys:
        role_keys.append(ROLE_BROKER)
    role_presets = dict(ROLE_PRESETS)
    role_presets.setdefault(
        ROLE_BROKER,
        ["manage_properties", "manage_leads", "manage_inquiries"],
    )
    role_options = role_options_for_ui()
    return render_template(
        "admin/admin_users.html",
        admins=admins,
        permission_keys=PERMISSION_KEYS,
        role_keys=role_keys,
        role_presets=role_presets,
        role_options=role_options,
        edit_admin_id=edit_id,
        setup_payload=setup_payload,
    )


@admin_bp.route("/employees/create", methods=["POST"])
@super_admin_required
def create_admin_user():
    try:
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        if not email and username:
            email = f"{username}@jakkash.local"
        created = Admin.create_admin(
            {
                "username": username,
                "email": email,
                "full_name": request.form.get("full_name"),
                "password": request.form.get("password"),
                "role": request.form.get("role"),
                "phone": request.form.get("phone"),
                "phone_verified": False,
                "is_active": True,
                "require_otp": False,
                "mobile_otp_enabled": False,
                "permissions": _permissions_from_form(request.form),
            },
            created_by_admin_id=current_user.id,
        )
        flash(f"Employee admin '{created.username}' created.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    except Exception:
        flash("Unable to create employee admin.", "danger")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/employees/<int:admin_id>/update", methods=["POST"])
@super_admin_required
def update_admin_user(admin_id):
    try:
        Admin.update_admin(
            admin_id,
            {
                "email": request.form.get("email"),
                "full_name": request.form.get("full_name"),
                "password": request.form.get("password"),
                "role": request.form.get("role"),
                "phone": request.form.get("phone"),
                "phone_verified": _parse_bool_form(request.form, "phone_verified"),
                "is_active": _parse_bool_form(request.form, "is_active"),
                "require_otp": _parse_bool_form(request.form, "require_otp"),
                "mobile_otp_enabled": _parse_bool_form(request.form, "mobile_otp_enabled"),
                "permissions": _permissions_from_form(request.form),
            },
        )
        flash("Employee admin updated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    except Exception:
        flash("Unable to update employee admin.", "danger")
    return redirect(url_for("admin.admin_users", edit=admin_id))


@admin_bp.route("/employees/<int:admin_id>/toggle-active", methods=["POST"])
@super_admin_required
def toggle_admin_user(admin_id):
    should_enable = _parse_bool_form(request.form, "is_active")
    try:
        Admin.toggle_active(admin_id, should_enable)
        flash("Employee status updated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/employees/<int:admin_id>/delete", methods=["POST"])
@super_admin_required
def delete_admin_user(admin_id):
    try:
        Admin.delete_admin(admin_id)
        flash("Employee admin deactivated.", "info")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/employees/<int:admin_id>/totp/setup", methods=["POST"])
@super_admin_required
def setup_admin_totp(admin_id):
    try:
        regenerate = _parse_bool_form(request.form, "regenerate")
        Admin.ensure_totp_secret(admin_id, regenerate=regenerate)
        flash("Google Authenticator setup generated.", "success")
    except ValueError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.admin_users", edit=admin_id, setup_admin=admin_id))


@admin_bp.route("/employees/<int:admin_id>/totp/disable", methods=["POST"])
@super_admin_required
def disable_admin_totp(admin_id):
    Admin.disable_totp(admin_id)
    flash("Google Authenticator disabled.", "warning")
    return redirect(url_for("admin.admin_users", edit=admin_id))


@admin_bp.route("/activity")
@super_admin_required
def activity_logs_dashboard():
    start_date = _coerce_iso_date(request.args.get("start_date"))
    end_date = _coerce_iso_date(request.args.get("end_date"))
    logs = activity_model.list_logs(
        limit=600,
        admin_id=request.args.get("admin_id", type=int),
        action_key=(request.args.get("action_key") or "").strip() or None,
        start_date=start_date,
        end_date=end_date,
    )
    return render_template(
        "admin/activity_logs.html",
        logs=logs,
        admins=Admin.list_admins(include_inactive=True),
        selected_admin_id=request.args.get("admin_id", type=int),
        selected_action=(request.args.get("action_key") or "").strip(),
        start_date=start_date or "",
        end_date=end_date or "",
    )


@admin_bp.route("/sellers", methods=["GET", "POST"])
@admin_bp.route("/sellers/<path:subpath>", methods=["GET", "POST"])
@admin_required
def sellers_disabled(subpath=None):
    return redirect(url_for("admin.sell_properties"))


@admin_bp.route("/visits", methods=["GET", "POST"])
@permission_required("manage_customer_visits")
def customer_visits():
    start_date = _coerce_iso_date(request.args.get("start_date"))
    end_date = _coerce_iso_date(request.args.get("end_date"))
    if request.method == "POST":
        property_ids = [int(x) for x in request.form.getlist("property_ids") if str(x).isdigit()]
        property_id = property_ids[0] if property_ids else request.form.get("property_id", type=int)
        linked_property = prop_model.get_by_id(property_id) if property_id else None
        if linked_property:
            _ensure_property_owner(linked_property)
        payload = {
            "visit_date": request.form.get("visit_date"),
            "client_name": request.form.get("client_name"),
            "client_address": request.form.get("client_address"),
            "client_contact": request.form.get("client_contact"),
            "client_requirement": request.form.get("client_requirement"),
            "property_id": property_id,
            "property_ids": property_ids,
            "executive_name": request.form.get("executive_name"),
            "executive_address": request.form.get("executive_address"),
            "executive_contact": request.form.get("executive_contact"),
            "customer_signature_label": request.form.get("customer_signature_label"),
            "executive_signature_label": request.form.get("executive_signature_label"),
            "customer_signature_data": request.form.get("customer_signature_data"),
            "executive_signature_data": request.form.get("executive_signature_data"),
        }
        required = [
            "visit_date",
            "client_name",
            "client_address",
            "client_contact",
            "client_requirement",
            "executive_name",
            "executive_address",
            "executive_contact",
        ]
        if not property_ids or any(not str(payload.get(field) or "").strip() for field in required):
            flash("Please complete all required customer visit fields and select at least one property.", "danger")
            return redirect(url_for("admin.customer_visits"))
        visit = visit_model.create_visit(payload, created_by_admin_id=current_user.id)
        _log_admin_action(
            "customer_visit_added",
            "Added customer visit form",
            entity_type="customer_visit",
            entity_id=(visit or {}).get("id"),
            meta={"client_name": payload.get("client_name"), "property_ids": property_ids},
        )
        flash("Customer visit form saved.", "success")
        return redirect(url_for("admin.customer_visits"))

    rows = visit_model.list_visits(limit=500, start_date=start_date, end_date=end_date)
    properties = prop_model.search(
        limit=500,
        all_statuses=True,
        status=None,
        owner_admin_id=_owner_scope_admin_id(),
    )
    return render_template(
        "admin/customer_visits.html",
        visits=rows,
        properties=properties,
        start_date=start_date or "",
        end_date=end_date or "",
    )


@admin_bp.route("/visits/<int:visit_id>/delete", methods=["POST"])
@permission_required("manage_customer_visits")
def delete_customer_visit(visit_id):
    visit = visit_model.get_visit(visit_id)
    if not visit:
        abort(404)
    visit_model.delete_visit(visit_id)
    _log_admin_action(
        "customer_visit_deleted",
        "Deleted customer visit form",
        entity_type="customer_visit",
        entity_id=visit_id,
    )
    flash("Customer visit deleted.", "warning")
    return redirect(url_for("admin.customer_visits"))


@admin_bp.route("/visits/<int:visit_id>/print")
@permission_required("manage_customer_visits")
def print_customer_visit(visit_id):
    visit = visit_model.get_visit(visit_id)
    if not visit:
        abort(404)
    _log_admin_action(
        "sensitive_visit_detail_view",
        "Viewed customer visit details",
        entity_type="customer_visit",
        entity_id=visit_id,
    )
    return render_template("admin/visit_print.html", visit=visit)


@admin_bp.route("/visits/<int:visit_id>/pdf")
@permission_required("manage_customer_visits")
def customer_visit_pdf(visit_id):
    visit = visit_model.get_visit(visit_id)
    if not visit:
        abort(404)
    lines = [
        f"Visit Date: {visit.get('visit_date')}",
        f"Client: {visit.get('client_name')} ({visit.get('client_contact')})",
        f"Client Address: {visit.get('client_address') or '-'}",
        f"Requirement: {visit.get('client_requirement') or '-'}",
        "Selected Properties:",
    ]
    selected = visit.get("selected_properties") or []
    if selected:
        for prop in selected:
            block_unit = " / ".join(
                x for x in [prop.get("block_wing"), prop.get("unit_number")] if x
            ) or "-"
            intent = "Rent" if (prop.get("listing_intent") or "").lower() == "rent" else "Sale"
            price = prop.get("price") or 0
            lines.append(
                f"  - {prop.get('property_name') or 'Property'} | "
                f"{prop.get('area_name') or '-'} | Block/Unit: {block_unit} | "
                f"{intent}: Rs {price:,.0f}"
            )
    else:
        lines.append(f"  - {(visit.get('property_names_display') or visit.get('property_name') or '-')}")
    lines.extend(
        [
            f"Executive: {visit.get('executive_name') or visit.get('linked_executive_name') or '-'}",
            f"Executive Contact: {visit.get('executive_contact') or '-'}",
            f"Executive Address: {visit.get('executive_address') or '-'}",
            f"Customer Signature: {visit.get('customer_signature_label') or 'Pending'}",
            f"Executive / Broker Signature: {visit.get('executive_signature_label') or 'Pending'}",
        ]
    )
    _log_admin_action(
        "visit_pdf_downloaded",
        "Downloaded customer visit PDF",
        entity_type="customer_visit",
        entity_id=visit_id,
    )
    return _pdf_download(f"customer-visit-{visit_id}.pdf", "Customer Visit Form", lines)


@admin_bp.route("/utilities")
@super_admin_required
def admin_utilities():
    return render_template("admin/utilities.html", counts=_mock_counts())


@admin_bp.route("/utilities/mock-flush", methods=["POST"])
@super_admin_required
def flush_mock_data():
    removed = _flush_mock_rows()
    total_removed = sum(removed.values())
    _log_admin_action(
        "mock_data_flushed",
        "Flushed mock data",
        entity_type="utility",
        meta={"removed": removed, "total_removed": total_removed},
    )
    flash(f"Mock-data flush completed. Removed {total_removed} rows.", "success")
    return redirect(url_for("admin.admin_utilities"))


def _form_property(form):
    amenities = [a.strip() for a in form.get("amenities", "").split(",") if a.strip()]

    def _required_float(field_name, label, min_value=None):
        raw = str(form.get(field_name) or "").strip().replace(",", "")
        if not raw:
            raise ValueError(f"{label} is required.")
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a valid number.") from exc
        if min_value is not None and value < min_value:
            raise ValueError(f"{label} must be at least {min_value}.")
        return value

    def _optional_float(field_name, label, default):
        raw = str(form.get(field_name) or "").strip().replace(",", "")
        if not raw:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a valid number.") from exc

    def _optional_int(field_name, label, default=0, min_value=None):
        raw = str(form.get(field_name) or "").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be a valid whole number.") from exc
        if min_value is not None and value < min_value:
            raise ValueError(f"{label} must be at least {min_value}.")
        return value

    return {
        "property_name": form.get("property_name"),
        "property_type": form.get("property_type"),
        "area_name": form.get("area_name"),
        "address": form.get("address"),
        "price": _required_float("price", "Price", min_value=0),
        "bhk": _optional_int("bhk", "BHK", default=0, min_value=0),
        "sq_ft": _required_float("sq_ft", "Area (sq ft)", min_value=1),
        "description": form.get("description"),
        "amenities": amenities,
        "latitude": _optional_float("latitude", "Latitude", 21.1702),
        "longitude": _optional_float("longitude", "Longitude", 72.8311),
        "status": form.get("status", "available"),
        "is_featured": form.get("is_featured") == "on",
        "listing_type": form.get("listing_type") or form.get("listing_intent") or "sale",
        "listing_intent": form.get("listing_intent") or form.get("listing_type") or "sell",
        "seller_type": form.get("seller_type") or None,
        "block_wing": (form.get("block_wing") or "").strip() or None,
        "unit_number": (form.get("unit_number") or "").strip() or None,
        "creation_source": form.get("creation_source", "admin"),
    }


def _upload_media(request, pid):
    for i, f in enumerate(request.files.getlist("images")):
        path = save_upload(f, pid, "images", ALLOWED_IMAGE)
        if path:
            prop_model.add_image(pid, path, is_primary=(i == 0), sort_order=i)
    for i, f in enumerate(request.files.getlist("videos")):
        path = save_upload(f, pid, "videos", ALLOWED_VIDEO)
        if path:
            prop_model.add_video(pid, path, sort_order=i)
    for f in request.files.getlist("documents"):
        path = save_upload(f, pid, "documents", ALLOWED_DOC)
        if path:
            prop_model.add_document(pid, path, f.filename)



def _ensure_submission_lead(submission):
    property_id = submission.get("property_id")
    if not property_id or not submission.get("owner_mobile"):
        return
    existing = query_one("SELECT id FROM leads WHERE property_id=%s LIMIT 1", (property_id,))
    if existing:
        return
    lead_model.create_from_inquiry(
        {
            "name": submission.get("owner_name") or "Property Owner",
            "mobile": submission.get("owner_mobile"),
            "email": submission.get("owner_email"),
            "budget": submission.get("price"),
            "preferred_area": submission.get("location_area") or submission.get("city"),
            "property_id": property_id,
        }
    )
