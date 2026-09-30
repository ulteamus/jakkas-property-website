"""Admin routes: lease toggle, amenities manager, billing receipts, WhatsApp promotions."""

from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from config import COMPANY_ADDRESS, COMPANY_NAME, COMPANY_PHONE, PROMO_COOLDOWN_DAYS, PROMO_STALE_DAYS
from models import amenity as amenity_model
from models import billing as billing_model
from models import promotion as promo_model
from models import property as prop_model
from models import submission as submission_model
from routes.admin_portal import (
    _ensure_property_owner,
    _log_admin_action,
    _pdf_bytes_download,
    admin_bp,
    permission_required,
)
from utils.pdf_export import generate_receipt_pdf

LEASE_TOGGLE_STATUSES = ("rented", "available")


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@admin_bp.route("/properties/<int:pid>/lease-status", methods=["POST"])
@permission_required("manage_properties")
def property_lease_status(pid):
    prop = prop_model.get_by_id(pid)
    _ensure_property_owner(prop)
    status = (request.form.get("status") or "").strip().lower()
    if status not in LEASE_TOGGLE_STATUSES:
        flash("Invalid status.", "danger")
        return redirect(url_for("admin.properties"))
    is_rent = (prop.get("listing_type") or "").lower() == "rent" or (
        prop.get("listing_intent") or ""
    ).lower() == "rent"
    if status == "rented" and not is_rent:
        flash("Only Rent listings can be marked Rented.", "warning")
        return redirect(url_for("admin.properties"))
    prop_model.set_status(pid, status)
    try:
        submission_model.sync_submission_from_property_status(pid, status, reviewed_by=current_user.id)
    except Exception:
        pass
    _log_admin_action(
        "property_lease_status",
        f"Marked property #{pid} as {status}",
        entity_type="property",
        entity_id=pid,
        meta={"status": status, "previous": prop.get("status")},
    )
    flash(f"Property marked as {status.title()}.", "success")
    return redirect(url_for("admin.properties"))


@admin_bp.route("/amenities", methods=["GET", "POST"])
@permission_required("manage_settings")
def amenities():
    if request.method == "POST":
        label = request.form.get("label")
        try:
            new_id = amenity_model.create(label, _int_or_none(request.form.get("sort_order")))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception:
            flash("Amenities table is not available. Apply the database migration first.", "danger")
        else:
            _log_admin_action(
                "amenity_create",
                f"Added amenity {amenity_model.normalize_label(label)}",
                entity_type="amenity",
                entity_id=new_id,
            )
            flash("Amenity added.", "success")
        return redirect(url_for("admin.amenities"))
    return render_template("admin/amenities.html", amenities=amenity_model.list_all())


@admin_bp.route("/amenities/<int:amenity_id>/edit", methods=["POST"])
@permission_required("manage_settings")
def amenity_edit(amenity_id):
    if not amenity_model.get(amenity_id):
        abort(404)
    label = request.form.get("label")
    try:
        amenity_model.update(amenity_id, label, _int_or_none(request.form.get("sort_order")))
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        _log_admin_action(
            "amenity_update",
            f"Updated amenity #{amenity_id}",
            entity_type="amenity",
            entity_id=amenity_id,
            meta={"label": amenity_model.normalize_label(label)},
        )
        flash("Amenity updated.", "success")
    return redirect(url_for("admin.amenities"))


@admin_bp.route("/amenities/<int:amenity_id>/toggle", methods=["POST"])
@permission_required("manage_settings")
def amenity_toggle(amenity_id):
    if not amenity_model.get(amenity_id):
        abort(404)
    is_active = amenity_model.toggle(amenity_id)
    _log_admin_action(
        "amenity_toggle",
        f"{'Enabled' if is_active else 'Disabled'} amenity #{amenity_id}",
        entity_type="amenity",
        entity_id=amenity_id,
    )
    flash("Amenity enabled." if is_active else "Amenity disabled.", "success")
    return redirect(url_for("admin.amenities"))


def _billing_unavailable():
    flash("Billing tables are not available. Apply the database migration first.", "warning")
    return redirect(url_for("admin.dashboard"))


def _get_receipt_or_404(receipt_id):
    receipt = billing_model.get_receipt(receipt_id)
    if not receipt:
        abort(404)
    return receipt


@admin_bp.route("/billing")
@permission_required("manage_billing")
def billing_list():
    if not billing_model.tables_available():
        return _billing_unavailable()
    status = (request.args.get("status") or "").strip().lower()
    valid = {
        billing_model.STATUS_UNPAID,
        billing_model.STATUS_PARTIAL,
        billing_model.STATUS_PAID,
        billing_model.STATUS_VOID,
    }
    if status not in valid:
        status = ""
    receipts = billing_model.list_receipts(limit=200, status=status or None)
    return render_template("admin/billing_list.html", receipts=receipts, selected_status=status or "all")


@admin_bp.route("/billing/new", methods=["GET", "POST"])
@permission_required("manage_billing")
def billing_new():
    if not billing_model.tables_available():
        return _billing_unavailable()
    property_id = _int_or_none(request.values.get("property_id"))
    prop = None
    if property_id:
        prop = prop_model.get_by_id(property_id)
        _ensure_property_owner(prop)

    if request.method == "POST":
        try:
            receipt = billing_model.create_receipt(request.form, current_user.id, prop)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("admin/billing_form.html", prop=prop, form=request.form)
        _log_admin_action(
            "billing_create",
            f"Created receipt {receipt.get('receipt_no')}",
            entity_type="billing_receipt",
            entity_id=receipt["id"],
            meta={"property_id": property_id, "total": str(receipt["total_amount"])},
        )
        flash(f"Receipt {receipt.get('receipt_no')} created.", "success")
        return redirect(url_for("admin.billing_detail", receipt_id=receipt["id"]))

    form = {}
    if prop:
        deal_type = billing_model.normalize_deal_type(prop.get("listing_type"))
        try:
            deal_amount = billing_model.to_money(prop.get("price") or 0)
        except ValueError:
            deal_amount = billing_model.to_money(0)
        form = {
            "deal_type": deal_type,
            "deal_amount": deal_amount,
            "brokerage_amount": billing_model.suggested_brokerage(deal_type, deal_amount),
            "property_name": prop.get("property_name") or "",
            "property_address": prop.get("address") or "",
        }
    return render_template("admin/billing_form.html", prop=prop, form=form)


@admin_bp.route("/billing/<int:receipt_id>")
@permission_required("manage_billing")
def billing_detail(receipt_id):
    receipt = _get_receipt_or_404(receipt_id)
    return render_template(
        "admin/billing_detail.html",
        receipt=receipt,
        payment_methods=billing_model.PAYMENT_METHODS,
        today=date.today().isoformat(),
    )


@admin_bp.route("/billing/<int:receipt_id>/payments", methods=["POST"])
@permission_required("manage_billing")
def billing_add_payment(receipt_id):
    _get_receipt_or_404(receipt_id)
    try:
        receipt = billing_model.add_payment(receipt_id, request.form, current_user.id)
    except ValueError as exc:
        flash(str(exc), "danger")
    else:
        _log_admin_action(
            "billing_payment",
            f"Recorded payment on {receipt.get('receipt_no')}",
            entity_type="billing_receipt",
            entity_id=receipt_id,
            meta={"amount": request.form.get("amount"), "status": receipt.get("status")},
        )
        flash("Payment recorded.", "success")
    return redirect(url_for("admin.billing_detail", receipt_id=receipt_id))


@admin_bp.route("/billing/<int:receipt_id>/void", methods=["POST"])
@permission_required("manage_billing")
def billing_void(receipt_id):
    _get_receipt_or_404(receipt_id)
    receipt = billing_model.void_receipt(receipt_id, request.form.get("reason"))
    _log_admin_action(
        "billing_void",
        f"Voided receipt {receipt.get('receipt_no')}",
        entity_type="billing_receipt",
        entity_id=receipt_id,
    )
    flash("Receipt voided.", "success")
    return redirect(url_for("admin.billing_detail", receipt_id=receipt_id))


@admin_bp.route("/billing/<int:receipt_id>/print")
@permission_required("manage_billing")
def billing_print(receipt_id):
    receipt = _get_receipt_or_404(receipt_id)
    return render_template(
        "admin/billing_print.html",
        receipt=receipt,
        company_name=COMPANY_NAME,
        company_address=COMPANY_ADDRESS,
        company_phone=COMPANY_PHONE,
    )


@admin_bp.route("/billing/<int:receipt_id>/pdf")
@permission_required("manage_billing")
def billing_pdf(receipt_id):
    receipt = _get_receipt_or_404(receipt_id)
    payload = generate_receipt_pdf(receipt, COMPANY_NAME, COMPANY_ADDRESS, COMPANY_PHONE)
    _log_admin_action(
        "billing_pdf",
        f"Downloaded receipt {receipt.get('receipt_no')}",
        entity_type="billing_receipt",
        entity_id=receipt_id,
    )
    return _pdf_bytes_download(f"receipt_{receipt.get('receipt_no') or receipt_id}.pdf", payload)


@admin_bp.route("/promotions")
@permission_required("manage_leads")
def promotions():
    stale = promo_model.stale_properties(PROMO_STALE_DAYS)
    property_id = _int_or_none(request.args.get("property_id"))
    selected = next((p for p in stale if int(p["id"]) == property_id), None) if property_id else None
    contacts = []
    skipped = {}
    if selected:
        result = promo_model.audience(PROMO_COOLDOWN_DAYS)
        base_url = request.url_root.rstrip("/")
        for contact in result["contacts"]:
            contact = dict(contact)
            contact["message"] = promo_model.build_message(selected, contact.get("name"), base_url)
            contacts.append(contact)
        skipped = result["skipped"]
    return render_template(
        "admin/promotions.html",
        stale_properties=stale,
        selected=selected,
        contacts=contacts,
        skipped=skipped,
        recent_log=promo_model.recent_log(50),
        stale_days=PROMO_STALE_DAYS,
        cooldown_days=PROMO_COOLDOWN_DAYS,
    )


@admin_bp.route("/promotions/send", methods=["POST"])
@permission_required("manage_leads")
def promotion_send():
    phone = promo_model.normalize_phone(request.form.get("phone"))
    property_id = _int_or_none(request.form.get("property_id"))
    prop = prop_model.get_by_id(property_id) if property_id else None
    if not phone or not prop or prop.get("status") not in prop_model.PUBLIC_LISTING_STATUSES:
        flash("Invalid contact or property.", "danger")
        return redirect(url_for("admin.promotions", property_id=property_id))
    if not promo_model.is_eligible(phone, PROMO_COOLDOWN_DAYS):
        flash("This contact opted out or was messaged recently.", "warning")
        return redirect(url_for("admin.promotions", property_id=property_id))
    name = (request.form.get("name") or "").strip()[:120]
    message = promo_model.build_message(prop, name, request.url_root.rstrip("/"))
    try:
        promo_model.record_send(
            phone,
            message,
            contact_name=name or None,
            source_type=(request.form.get("source_type") or "")[:20] or None,
            source_id=_int_or_none(request.form.get("source_id")),
            property_id=property_id,
            admin_id=current_user.id,
        )
    except Exception:
        flash("Promotion log table is not available. Apply the database migration first.", "danger")
        return redirect(url_for("admin.promotions", property_id=property_id))
    _log_admin_action(
        "promotion_send",
        f"WhatsApp promo for property #{property_id}",
        entity_type="property",
        entity_id=property_id,
        meta={"phone_suffix": phone[-4:]},
    )
    return redirect(promo_model.wa_link(phone, message))


@admin_bp.route("/promotions/opt-out", methods=["POST"])
@permission_required("manage_leads")
def promotion_opt_out():
    phone = promo_model.normalize_phone(request.form.get("phone"))
    property_id = _int_or_none(request.form.get("property_id"))
    if not phone:
        flash("Invalid phone number.", "danger")
    else:
        opted_out = (request.form.get("opted_out") or "1") != "0"
        try:
            promo_model.set_opt_out(phone, opted_out, source="admin")
        except Exception:
            flash("Opt-in table is not available. Apply the database migration first.", "danger")
        else:
            _log_admin_action(
                "promotion_opt_out",
                "WhatsApp opt-out updated",
                meta={"phone_suffix": phone[-4:], "opted_out": opted_out},
            )
            flash("Contact opted out." if opted_out else "Contact opted back in.", "success")
    return redirect(url_for("admin.promotions", property_id=property_id))
