"""Focused tests: billing math, amenities CRUD, lease toggle, promo eligibility.

Writes to the configured database; run only against a disposable local SQLite
instance (USE_SQLITE=1, no Postgres URL).
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from database import query_one  # noqa: E402
from database.supabase_client import postgres_configured  # noqa: E402
from models import amenity as amenity_model  # noqa: E402
from models import billing as billing_model  # noqa: E402
from models import lead as lead_model  # noqa: E402
from models import promotion as promo_model  # noqa: E402
from models import property as prop_model  # noqa: E402

assert not postgres_configured(), "Refusing to run against Postgres"

APP = create_app()
APP.config["WTF_CSRF_ENABLED"] = False


def _raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except ValueError:
        return True
    return False


def _any_public_property(listing_type=None):
    sql = "SELECT id FROM properties WHERE status IN ('available','approved','active')"
    params = []
    if listing_type == "rent":
        sql += " AND listing_type='rent'"
    elif listing_type == "sale":
        sql += " AND COALESCE(listing_type,'')<>'rent' AND COALESCE(listing_intent,'')<>'rent'"
    row = query_one(sql + " ORDER BY id LIMIT 1", params)
    assert row, f"Seed data needs at least one public {listing_type or ''} property"
    return prop_model.get_by_id(row["id"])


def test_money_and_brokerage_math():
    assert billing_model.to_money("333.335") == Decimal("333.34")
    assert billing_model.to_money("0") == Decimal("0.00")
    assert _raises(billing_model.to_money, "-1")
    assert _raises(billing_model.to_money, "abc")
    assert _raises(billing_model.to_money, "NaN")
    assert _raises(billing_model.to_money, "0", "Payment", allow_zero=False)
    assert billing_model.suggested_brokerage("sale", "5000000") == Decimal("100000.00")
    assert billing_model.suggested_brokerage("rent", "25000") == Decimal("25000.00")
    assert billing_model.suggested_brokerage("sale", "1234567.89") == Decimal("24691.36")

    no_gst = billing_model.compute_totals("100000", gst_enabled=False)
    assert no_gst["gst_amount"] == Decimal("0.00")
    assert no_gst["total_amount"] == Decimal("100000.00")
    gst = billing_model.compute_totals("100000", gst_enabled=True)
    assert gst["gst_amount"] == Decimal("18000.00")
    assert gst["total_amount"] == Decimal("118000.00")
    odd = billing_model.compute_totals("24691.36", gst_enabled=True)
    assert odd["gst_amount"] == Decimal("4444.44")
    assert odd["total_amount"] == Decimal("29135.80")

    pending = billing_model.compute_pending(Decimal("118000.00"), [{"amount": Decimal("18000.10")}])
    assert pending["paid_total"] == Decimal("18000.10")
    assert pending["pending"] == Decimal("99999.90")
    assert billing_model.status_for(Decimal("100"), Decimal("0")) == "unpaid"
    assert billing_model.status_for(Decimal("100"), Decimal("40")) == "partial"
    assert billing_model.status_for(Decimal("100"), Decimal("100")) == "paid"


def test_receipt_lifecycle():
    with APP.app_context():
        prop = _any_public_property()
        receipt = billing_model.create_receipt(
            {"client_name": "Test Buyer", "deal_type": "sale", "deal_amount": "5000000", "gst_enabled": "1"},
            created_by_admin_id=None,
            property_row=prop,
        )
        assert receipt["receipt_no"].startswith("JK-")
        assert receipt["property_name"] == prop["property_name"]
        assert receipt["brokerage_amount"] == Decimal("100000.00")
        assert receipt["total_amount"] == Decimal("118000.00")
        assert receipt["pending"] == Decimal("118000.00")
        assert receipt["status"] == "unpaid"

        rid = receipt["id"]
        assert _raises(billing_model.add_payment, rid, {"amount": "118000.01"})
        assert _raises(billing_model.add_payment, rid, {"amount": "10", "payment_date": "2026-13-40"})
        after = billing_model.add_payment(rid, {"amount": "18000", "method": "upi"})
        assert after["status"] == "partial"
        assert after["pending"] == Decimal("100000.00")
        after = billing_model.add_payment(rid, {"amount": "100000", "method": "bank_transfer"})
        assert after["status"] == "paid"
        assert after["pending"] == Decimal("0.00")
        assert len(after["payments"]) == 2

        custom = billing_model.create_receipt(
            {"client_name": "Tenant", "deal_type": "rent", "deal_amount": "20000", "brokerage_amount": "15000"}
        )
        assert custom["brokerage_amount"] == Decimal("15000.00")
        assert custom["gst_enabled"] is False
        assert custom["total_amount"] == Decimal("15000.00")
        voided = billing_model.void_receipt(custom["id"], "duplicate")
        assert voided["status"] == "void"
        assert _raises(billing_model.add_payment, custom["id"], {"amount": "1"})
        assert _raises(billing_model.create_receipt, {"client_name": "", "deal_amount": "1"})


def test_amenities_crud_and_validation():
    with APP.app_context():
        label = f"Jacuzzi {random.randint(1000, 9999)}"
        new_id = amenity_model.create(label)
        assert new_id
        assert label in amenity_model.list_active_labels()
        assert _raises(amenity_model.create, label.lower())
        assert _raises(amenity_model.create, "   ")
        assert _raises(amenity_model.create, "<script>")
        assert _raises(amenity_model.create, "x" * 61)

        amenity_model.update(new_id, label + " Deluxe", 5)
        assert amenity_model.get(new_id)["label"] == label + " Deluxe"
        assert _raises(amenity_model.update, new_id, "Parking")

        assert amenity_model.toggle(new_id) is False
        assert label + " Deluxe" not in amenity_model.list_active_labels()
        assert label + " Deluxe" in amenity_model.labels_for_form([label + " Deluxe"])
        assert amenity_model.toggle(new_id) is True
        assert label + " Deluxe" in amenity_model.list_active_labels()


def test_lease_toggle_hides_from_public():
    prop = None
    with APP.app_context():
        prop = prop_model.create(
            {
                "property_name": "Lease Toggle Temp Rent",
                "property_type": "flat",
                "area_name": "Adajan",
                "price": 25000,
                "sq_ft": 900,
                "listing_intent": "rent",
                "listing_type": "rent",
                "status": "available",
            }
        )
    client = APP.test_client()
    resp = client.post("/admin/login", data={"username": "sam", "password": "admin123"})
    assert resp.status_code in (302, 303), resp.status_code
    try:
        resp = client.post(f"/admin/properties/{prop['id']}/lease-status", data={"status": "rented"})
        assert resp.status_code == 302
        with APP.app_context():
            assert prop_model.get_by_id(prop["id"])["status"] == "rented"
        api_ids = {p["id"] for p in client.get("/api/properties?limit=100").get_json().get("properties", [])}
        assert prop["id"] not in api_ids
        leaked = client.get("/api/properties?status=rented&limit=100").get_json().get("properties", [])
        assert all(p.get("status") != "rented" for p in leaked)
        admin_page = client.get("/admin/properties?status=rented").get_data(as_text=True)
        assert prop["property_name"] in admin_page
        assert client.post(f"/admin/properties/{prop['id']}/lease-status", data={"status": "sold"}).status_code == 302
        with APP.app_context():
            assert prop_model.get_by_id(prop["id"])["status"] == "rented"
        client.post(f"/admin/properties/{prop['id']}/lease-status", data={"status": "available"})
        with APP.app_context():
            assert prop_model.get_by_id(prop["id"])["status"] == "available"
    finally:
        with APP.app_context():
            prop_model.delete(prop["id"])


def test_promo_eligibility_and_cooldown():
    with APP.app_context():
        now = datetime.utcnow()
        assert promo_model.normalize_phone("098765 43210") == "919876543210"
        assert promo_model.normalize_phone("+91 98765-43210") == "919876543210"
        assert promo_model.normalize_phone("12345") is None

        stale_now = promo_model.stale_properties(30, now=now + timedelta(days=3650))
        assert stale_now, "All seeded public properties should be stale ten years out"
        assert promo_model.stale_properties(30, now=now - timedelta(days=3650)) == []

        mobile = f"9{random.randint(100000000, 999999999)}"
        phone = promo_model.normalize_phone(mobile)
        lead_model.create_from_inquiry({"name": "Promo Tester", "mobile": mobile})
        contacts = {c["phone"] for c in promo_model.audience(7)["contacts"]}
        assert phone in contacts
        assert promo_model.is_eligible(phone, 7)

        prop = stale_now[0]
        message = promo_model.build_message(prop, "Promo Tester", "http://127.0.0.1:5001")
        assert "STOP" in message
        assert promo_model.wa_link(phone, message).startswith(f"https://wa.me/{phone}?text=")
        promo_model.record_send(phone, message, contact_name="Promo Tester", property_id=prop["id"])

        assert not promo_model.is_eligible(phone, 7)
        assert phone not in {c["phone"] for c in promo_model.audience(7)["contacts"]}
        assert promo_model.is_eligible(phone, 7, now=now + timedelta(days=8))
        assert any(r["phone"] == phone for r in promo_model.recent_log(20))

        promo_model.set_opt_out(phone, True)
        assert not promo_model.is_eligible(phone, 7, now=now + timedelta(days=8))
        promo_model.set_opt_out(phone, False)
        assert promo_model.is_eligible(phone, 7, now=now + timedelta(days=8))


TESTS = [
    test_money_and_brokerage_math,
    test_receipt_lifecycle,
    test_amenities_crud_and_validation,
    test_lease_toggle_hides_from_public,
    test_promo_eligibility_and_cooldown,
]


if __name__ == "__main__":
    failed = 0
    for test in TESTS:
        try:
            test()
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed += 1
            import traceback

            traceback.print_exc()
            print(f"FAIL {test.__name__}: {type(exc).__name__}: {exc}")
    print(f"summary_passed={len(TESTS) - failed}/{len(TESTS)}")
    raise SystemExit(1 if failed else 0)
