"""Round-2 features: client GSTIN, admin bell notifications, consented lead capture,
farmhouse filter, homepage stats.

Writes to the configured database; run only against a disposable local SQLite
instance (USE_SQLITE=1, no Postgres URL).
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from database import execute, query_all, query_one  # noqa: E402
from database.supabase_client import postgres_configured  # noqa: E402
from models import billing as billing_model  # noqa: E402
from models import notification as notif_model  # noqa: E402
from models import property as prop_model  # noqa: E402
from utils.rate_limit import reset_rate_limits  # noqa: E402

assert not postgres_configured(), "Refusing to run against Postgres"

APP = create_app()
APP.config["WTF_CSRF_ENABLED"] = False

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}


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


def _count(sql, params=()):
    return int((query_one(sql, params) or {}).get("n") or 0)


def test_gstin_validation_and_storage():
    assert billing_model.normalize_gstin("  24abcde1234f1z5 ") == "24ABCDE1234F1Z5"
    assert billing_model.normalize_gstin("") is None
    assert billing_model.normalize_gstin(None) is None
    for bad in ("24ABCDE1234F1Z", "ABCDE1234F1Z524", "24ABCDE1234F0Z5", "24ABCDE1234F1X5"):
        assert _raises(billing_model.normalize_gstin, bad), bad
    with APP.app_context():
        assert _raises(billing_model.create_receipt, {"client_name": "Bad GST", "deal_amount": "1000", "client_gstin": "XYZ"})
        receipt = billing_model.create_receipt(
            {"client_name": "GST Client", "deal_type": "sale", "deal_amount": "1000000", "client_gstin": "24abcde1234f1z5"}
        )
        try:
            assert receipt["client_gstin"] == "24ABCDE1234F1Z5"
            assert not receipt["gst_enabled"], "GST must stay off unless toggled"
            client = _login()
            html = client.get(f"/admin/billing/{receipt['id']}/print").get_data(as_text=True)
            assert "24ABCDE1234F1Z5" in html and "GSTIN" in html
            pdf = client.get(f"/admin/billing/{receipt['id']}/pdf")
            assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF"
            plain = billing_model.create_receipt({"client_name": "No GST", "deal_amount": "5000"})
            try:
                assert plain["client_gstin"] is None
                assert "GSTIN" not in client.get(f"/admin/billing/{plain['id']}/print").get_data(as_text=True)
            finally:
                execute("DELETE FROM billing_receipts WHERE id=%s", (plain["id"],))
        finally:
            execute("DELETE FROM billing_receipts WHERE id=%s", (receipt["id"],))


def test_sell_submission_notification():
    with APP.app_context():
        sub_id = 900000 + uuid.uuid4().int % 99999
        assert notif_model.notify_sell_submission(sub_id, "Test Owner", "Vesu", "flat") is True
        assert notif_model.notify_sell_submission(sub_id, "Test Owner", "Vesu", "flat") is False
        rows = query_all("SELECT * FROM admin_notifications WHERE dedupe_key=%s", (f"sell_submission:{sub_id}",))
        assert len(rows) == 1
        assert rows[0]["kind"] == notif_model.KIND_SELL_SUBMISSION
        assert "Vesu" in (rows[0]["body"] or "")
        execute("DELETE FROM admin_notifications WHERE dedupe_key=%s", (f"sell_submission:{sub_id}",))


def test_visitor_event_throttle_and_bot_filter():
    assert notif_model.is_probable_bot("Googlebot/2.1", "en")
    assert notif_model.is_probable_bot(BROWSER_HEADERS["User-Agent"], None)
    assert not notif_model.is_probable_bot(BROWSER_HEADERS["User-Agent"], "en-IN")
    with APP.app_context():
        before = _count("SELECT COUNT(*) AS n FROM admin_notifications WHERE kind=%s", (notif_model.KIND_SELL_PAGE_OPEN,))
        client = APP.test_client()
        assert client.get("/sell-property", headers=BROWSER_HEADERS).status_code == 200
        assert client.get("/sell-property", headers=BROWSER_HEADERS).status_code == 200
        after_human = _count("SELECT COUNT(*) AS n FROM admin_notifications WHERE kind=%s", (notif_model.KIND_SELL_PAGE_OPEN,))
        assert after_human == before + 1, (before, after_human)
        with client.session_transaction() as sess:
            visitor = sess["visitor_id"]
            sess.pop("_sell_open_bucket", None)
        assert client.get("/sell-property", headers=BROWSER_HEADERS).status_code == 200
        assert _count("SELECT COUNT(*) AS n FROM admin_notifications WHERE kind=%s", (notif_model.KIND_SELL_PAGE_OPEN,)) == after_human, \
            "Same visitor must not alert twice in one hour"
        bot = APP.test_client()
        assert bot.get("/sell-property", headers={"User-Agent": "Googlebot/2.1"}).status_code == 200
        assert _count("SELECT COUNT(*) AS n FROM admin_notifications WHERE kind=%s", (notif_model.KIND_SELL_PAGE_OPEN,)) == after_human
        execute("DELETE FROM admin_notifications WHERE dedupe_key LIKE %s", (f"sell_open:{visitor}:%",))


def test_lead_capture_requires_consent():
    reset_rate_limits()
    phone = "98" + str(uuid.uuid4().int)[:8]
    with APP.app_context():
        client = APP.test_client()
        resp = client.post("/api/lead-capture", json={"phone": phone, "name": "Visitor", "consent": False})
        assert resp.status_code == 400
        resp = client.post("/api/lead-capture", json={"phone": phone, "name": "Visitor"})
        assert resp.status_code == 400
        assert _count("SELECT COUNT(*) AS n FROM lead_captures WHERE phone=%s", (f"91{phone}",)) == 0
        assert client.post("/api/lead-capture", json={"phone": "123", "consent": True}).status_code == 400
        resp = client.post("/api/lead-capture", json={"phone": phone, "name": "<b>Visitor</b>", "consent": True})
        assert resp.status_code == 200, resp.get_data(as_text=True)
        row = query_one("SELECT * FROM lead_captures WHERE phone=%s", (f"91{phone}",))
        assert row and row["name"] == "Visitor" and row["consent_text"]
        note = query_one("SELECT * FROM admin_notifications WHERE kind=%s ORDER BY id DESC LIMIT 1", (notif_model.KIND_LEAD_CAPTURE,))
        assert note and phone not in (note["body"] or ""), "Full phone must be masked in the bell"
        execute("DELETE FROM lead_captures WHERE phone=%s", (f"91{phone}",))
        execute("DELETE FROM admin_notifications WHERE dedupe_key LIKE %s", (f"capture:91{phone}:%",))
    reset_rate_limits()


def test_farmhouse_filter_combines_with_intent():
    with APP.app_context():
        prop_model._ensure_schema()
        farm = prop_model.create(
            {
                "property_name": "Round2 Farmhouse",
                "property_type": "farmhouse",
                "area_name": "Dumas",
                "price": 9000000,
                "sq_ft": 5000,
                "listing_intent": "buy",
                "listing_type": "sale",
                "status": "available",
            }
        )
    try:
        client = APP.test_client()
        ids = lambda url: {p["id"] for p in client.get(url).get_json().get("properties", [])}  # noqa: E731
        typed = client.get("/api/properties?type=farmhouse&limit=100").get_json().get("properties", [])
        assert farm["id"] in {p["id"] for p in typed}
        assert all("farm" in (p.get("property_type") or "").lower() for p in typed)
        assert farm["id"] in ids("/api/properties?type=farmhouse&listing_intent=buy&limit=100")
        assert farm["id"] not in ids("/api/properties?type=farmhouse&listing_intent=rent&limit=100")
        page = client.get("/properties").get_data(as_text=True)
        assert 'data-quick-type="farmhouse"' in page and 'id="activeFilterCount"' in page
    finally:
        with APP.app_context():
            prop_model.delete(farm["id"])


def test_home_stats_values():
    page = APP.test_client().get("/").get_data(as_text=True)
    assert 'data-counter="500"' in page or ">500<" in page, "Properties/clients stat should be 500"
    assert "Happy Clients" in page
    assert 'data-counter="10"' in page or ">10<" in page
    with APP.app_context():
        from models import analytics as analytics_model

        assert analytics_model.home_kpi_counts() == {"properties": 500, "clients": 500, "years": 10}


def test_bell_api_auth_and_seen():
    anon = APP.test_client()
    assert anon.get("/admin/api/notifications").status_code == 401
    assert anon.post("/admin/api/notifications/seen", json={}).status_code == 401
    with APP.app_context():
        notif_model.create("test", "Bell test", dedupe_key=f"bell_test:{uuid.uuid4()}")
    client = _login()
    data = client.get("/admin/api/notifications").get_json()
    assert data["success"] and data["unread"] >= 1 and data["items"]
    top = max(int(i["id"]) for i in data["items"])
    assert client.post("/admin/api/notifications/seen", json={"up_to_id": top}).get_json()["success"]
    assert client.get("/admin/api/notifications").get_json()["unread"] == 0
    assert "adminNotifications" in client.get("/admin/").get_data(as_text=True)
    with APP.app_context():
        execute("DELETE FROM admin_notifications WHERE kind=%s", ("test",))


def test_static_links_are_versioned():
    page = APP.test_client().get("/").get_data(as_text=True)
    assert "/static/js/app.js?v=" in page or "app.js?v=" in page
    assert APP.config["ASSET_VERSION"]


TESTS = [
    test_gstin_validation_and_storage,
    test_sell_submission_notification,
    test_visitor_event_throttle_and_bot_filter,
    test_lead_capture_requires_consent,
    test_farmhouse_filter_combines_with_intent,
    test_home_stats_values,
    test_bell_api_auth_and_seen,
    test_static_links_are_versioned,
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
