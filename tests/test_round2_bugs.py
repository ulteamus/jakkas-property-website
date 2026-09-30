"""Round-2 bug fixes: Save Property form nesting, listing intent integrity, Rented rules.

Writes to the configured database; run only against a disposable local SQLite
instance (USE_SQLITE=1, no Postgres URL).
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

from werkzeug.datastructures import MultiDict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from database import execute, query_one  # noqa: E402
from database.supabase_client import postgres_configured  # noqa: E402
from models import property as prop_model  # noqa: E402
from routes.admin_portal import _form_property  # noqa: E402

assert not postgres_configured(), "Refusing to run against Postgres"

APP = create_app()
APP.config["WTF_CSRF_ENABLED"] = False


def _temp_rent_property():
    return prop_model.create(
        {
            "property_name": "Round2 Temp Rent",
            "property_type": "flat",
            "area_name": "Adajan",
            "price": 25000,
            "sq_ft": 900,
            "listing_intent": "rent",
            "listing_type": "rent",
            "status": "available",
        }
    )


def _public_property(kind):
    prop_model._ensure_schema()
    if kind == "rent":
        cond = "listing_type='rent'"
    else:
        cond = "COALESCE(listing_type,'')<>'rent' AND COALESCE(listing_intent,'')<>'rent'"
    row = query_one(
        "SELECT id FROM properties WHERE status IN ('available','approved','active') "
        f"AND {cond} ORDER BY id LIMIT 1"
    )
    assert row, f"Seed data needs a public {kind} property"
    return prop_model.get_by_id(row["id"])


def _login():
    client = APP.test_client()
    resp = client.post("/admin/login", data={"username": "sam", "password": "admin123"})
    assert resp.status_code in (302, 303), resp.status_code
    return client


def _raises(fn, *args):
    try:
        fn(*args)
    except ValueError as exc:
        return str(exc)
    return None


class _FormScan(HTMLParser):
    """Tracks form nesting and which named inputs/buttons belong to the main form."""

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.max_depth = 0
        self.stack = []
        self.main_fields = set()
        self.main_has_submit = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.depth += 1
            self.max_depth = max(self.max_depth, self.depth)
            self.stack.append(a.get("id"))
            return
        in_main = bool(self.stack) and self.stack[-1] == "adminPropertyForm"
        if in_main and tag in {"input", "select", "textarea"} and a.get("name"):
            self.main_fields.add(a["name"])
        if in_main and tag == "button" and a.get("type") == "submit" and not a.get("form"):
            self.main_has_submit = True

    def handle_endtag(self, tag):
        if tag == "form" and self.stack:
            self.depth -= 1
            self.stack.pop()


def test_property_form_not_nested_with_images():
    with APP.app_context():
        prop = _public_property("sale")
        img_id = execute(
            "INSERT INTO property_images (property_id, file_path, sort_order) VALUES (%s,%s,%s)",
            (prop["id"], "uploads/test-round2.jpg", 99),
        )
    try:
        html = _login().get(f"/admin/properties/{prop['id']}/edit").get_data(as_text=True)
        scan = _FormScan()
        scan.feed(html)
        assert scan.max_depth == 1, f"nested form depth {scan.max_depth}"
        assert {"status", "listing_intent", "listing_type"} <= scan.main_fields, scan.main_fields
        assert scan.main_has_submit, "Save Property button is outside the main form"
        assert f'id="imgDel{img_id}"' in html and f'form="imgDel{img_id}"' in html
    finally:
        with APP.app_context():
            execute("DELETE FROM property_images WHERE id=%s", (img_id,))


def test_form_property_status_rules():
    base = {
        "property_name": "Round2 Test",
        "area_name": "Adajan",
        "property_type": "flat",
        "price": "5000000",
        "sq_ft": "1200",
        "area_sq_ft": "1200",
    }
    with APP.test_request_context():
        ok = _form_property(MultiDict({**base, "listing_type": "sale", "status": "pending"}))
        assert ok["status"] == "reserved"
        assert _raises(_form_property, MultiDict({**base, "listing_type": "sale", "status": "bogus"})) == "Invalid status."
        err = _raises(_form_property, MultiDict({**base, "listing_type": "sale", "status": "rented"}))
        assert err and "Rent listings" in err
        rent = _form_property(MultiDict({**base, "listing_type": "rent", "status": "rented"}))
        assert rent["status"] == "rented" and rent["listing_type"] == "rent"


def test_search_intent_filter_and_labels():
    with APP.app_context():
        prop = _public_property("sale")
        execute("UPDATE properties SET listing_intent='rent' WHERE id=%s", (prop["id"],))
        try:
            rent_rows = prop_model.search(listing_intent="rent", limit=500)
            assert prop["id"] in {r["id"] for r in rent_rows}
            assert all(r["listing_intent"] == "rent" for r in rent_rows)
            buy_rows = prop_model.search(listing_intent="buy", limit=500)
            assert prop["id"] not in {r["id"] for r in buy_rows}
            assert all(r["listing_intent"] == "sell" for r in buy_rows)
        finally:
            execute("UPDATE properties SET listing_intent='sell' WHERE id=%s", (prop["id"],))


def test_update_keeps_unsent_fields():
    with APP.app_context():
        prop = _public_property("sale")
        before = prop_model.get_by_id(prop["id"])
        prop_model.update(prop["id"], {"price": float(before["price"]) + 1})
        after = prop_model.get_by_id(prop["id"])
        try:
            for key in ("latitude", "longitude", "city", "unit_number", "seller_type",
                        "listing_type", "listing_intent", "status", "property_name"):
                assert after.get(key) == before.get(key), key
            assert float(after["price"]) == float(before["price"]) + 1
        finally:
            prop_model.update(prop["id"], {"price": before["price"]})


def test_mark_rented_rejected_for_sale():
    with APP.app_context():
        prop = _public_property("sale")
    client = _login()
    resp = client.post(f"/admin/properties/{prop['id']}/lease-status", data={"status": "rented"})
    assert resp.status_code == 302
    with APP.app_context():
        assert prop_model.get_by_id(prop["id"])["status"] == prop["status"]
    page = client.get("/admin/properties?limit=500").get_data(as_text=True)
    assert f'/admin/properties/{prop["id"]}/lease-status' not in page, "Mark Rented shown for a Sale listing"

    with APP.app_context():
        rent = _temp_rent_property()
    try:
        page = client.get("/admin/properties?limit=500").get_data(as_text=True)
        assert f'/admin/properties/{rent["id"]}/lease-status' in page, "Mark Rented missing for a Rent listing"
        client.post(f"/admin/properties/{rent['id']}/lease-status", data={"status": "rented"})
        with APP.app_context():
            assert prop_model.get_by_id(rent["id"])["status"] == "rented"
    finally:
        with APP.app_context():
            prop_model.delete(rent["id"])


TESTS = [
    test_property_form_not_nested_with_images,
    test_form_property_status_rules,
    test_search_intent_filter_and_labels,
    test_update_keeps_unsent_fields,
    test_mark_rented_rejected_for_sale,
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
