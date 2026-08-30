"""Regression checks for client-feedback fixes (copy, sell flash, approve, reviews)."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("USE_SQLITE", "1")
os.environ.setdefault("FLASK_SECRET_KEY", "verify-client-fixes-secret")
os.environ.setdefault("FLASK_ENV", "development")

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from app import create_app
from database import query_one
from models import property as prop_model
from models import reviews as reviews_model
from models import submission as submission_model


SMOKE_CASES = [
    ("GET", "/", {200}),
    ("GET", "/properties", {200}),
    ("GET", "/contact", {200}),
    ("GET", "/about", {200}),
    ("GET", "/static/uploads/hero-fallback.jpg", {200}),
    ("GET", "/admin/login", {200}),
    ("GET", "/login", {404, 302, 301}),
    ("GET", "/api/properties", {200}),
]


def _session_flashes(client):
    with client.session_transaction() as sess:
        return list(sess.get("_flashes") or [])


def main() -> int:
    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    failed = 0
    results = {}

    with app.test_client() as client:
        # 1) Contact copy
        resp = client.get("/contact")
        body = resp.get_data(as_text=True) or ""
        contact_ok = (
            resp.status_code == 200
            and "Contact Us" in body
            and "Send Message" in body
            and "Request Site Visit" not in body
            and "Submit Site Visit" not in body
        )
        results["contact_copy"] = contact_ok
        print(("PASS" if contact_ok else "FAIL") + " contact copy (/contact)")
        if not contact_ok:
            failed += 1

        # 2) Sell-property success path (no false danger flash)
        token = uuid.uuid4().hex[:8]
        title = f"Verify Client Fix Flat {token}"
        address = f"{token} Regression Lane, Surat"
        post = client.post(
            "/sell-property",
            data={
                "owner_name": "Verify Owner",
                "owner_mobile": "9876543210",
                "owner_email": "verify@example.com",
                "owner_address": "Surat",
                "property_title": title,
                "property_type": "flat",
                "area_sq_ft": "1200",
                "area_value": "1200",
                "area_unit": "sq_ft",
                "price": "5500000",
                "property_address": address,
                "city": "Surat",
                "location_area": "Adajan",
                "listing_intent": "sell",
                "seller_type": "owner",
                "bhk": "3",
                "description": "Client-fix verification listing",
            },
            follow_redirects=False,
        )
        flashes = _session_flashes(client)
        danger = [msg for cat, msg in flashes if cat == "danger"]
        success = [msg for cat, msg in flashes if cat == "success"]
        pending = query_one(
            "SELECT * FROM properties WHERE property_name=%s ORDER BY id DESC LIMIT 1",
            (title,),
        )
        sell_ok = (
            post.status_code in {200, 302}
            and pending is not None
            and (pending.get("status") or "").lower() == "reserved"
            and not danger
            and any("submitted successfully" in (m or "").lower() for m in success)
        )
        results["sell_property_submit"] = {
            "ok": sell_ok,
            "status": post.status_code,
            "property_id": (pending or {}).get("id"),
            "prop_status": (pending or {}).get("status"),
            "danger": danger,
            "success": success,
        }
        print(("PASS" if sell_ok else "FAIL") + " sell-property submit")
        if not sell_ok:
            failed += 1

        # 3) Approve → available (+ is_active when column exists) → public API
        approve_ok = False
        property_id = (pending or {}).get("id")
        if property_id:
            prop_model.publish_approved(property_id)
            sub = query_one(
                "SELECT id FROM owner_submissions WHERE property_id=%s ORDER BY id DESC LIMIT 1",
                (property_id,),
            )
            if sub:
                try:
                    submission_model.set_submission_status(
                        sub["id"],
                        "approved",
                        reviewed_by=None,
                        review_note="verify_client_fixes",
                    )
                except Exception as exc:
                    results["approve_submission_status_error"] = str(exc)
            row = prop_model.get_by_id(property_id) or {}
            status_ok = (row.get("status") or "").lower() == "available"
            active_ok = True
            if "is_active" in row and row.get("is_active") is not None:
                active_ok = bool(row.get("is_active")) in (True, 1, "1")
            api = client.get("/api/properties")
            api_body = api.get_data(as_text=True) or ""
            listed = str(property_id) in api_body or title in api_body
            props_page = client.get("/properties")
            page_ok = props_page.status_code == 200
            approve_ok = status_ok and active_ok and listed and page_ok
            results["approve_publish"] = {
                "ok": approve_ok,
                "status": row.get("status"),
                "is_active": row.get("is_active"),
                "listed_in_api": listed,
            }
        else:
            results["approve_publish"] = {"ok": False, "error": "no pending property"}
        print(("PASS" if approve_ok else "FAIL") + " approve publish visibility")
        if not approve_ok:
            failed += 1

        # 4) Testimonial persistence
        marker = f"Verify review {uuid.uuid4().hex[:8]}"
        rid = reviews_model.create_review(
            "Verify Client",
            "Surat",
            marker,
            rating=5,
            is_active=True,
        )
        feed = reviews_model.list_reviews(limit=50) or []
        in_feed = any(marker in (r.get("review_text") or "") for r in feed)
        home = client.get("/")
        home_body = home.get_data(as_text=True) or ""
        review_ok = bool(rid) and in_feed and home.status_code == 200 and (
            marker in home_body or in_feed
        )
        results["testimonials"] = {
            "ok": review_ok,
            "review_id": rid,
            "in_feed": in_feed,
            "home_contains": marker in home_body,
        }
        print(("PASS" if review_ok else "FAIL") + " testimonial persistence")
        if not review_ok:
            failed += 1

        # 5) Core smoke routes
        smoke_failed = 0
        smoke = []
        for method, path, ok_statuses in SMOKE_CASES:
            r = client.open(path, method=method)
            ok = r.status_code in ok_statuses
            smoke.append({"path": path, "status": r.status_code, "ok": ok})
            flag = "PASS" if ok else "FAIL"
            print(f"{flag} smoke {method} {path} -> {r.status_code}")
            if not ok:
                smoke_failed += 1
        results["smoke"] = {"ok": smoke_failed == 0, "cases": smoke}
        if smoke_failed:
            failed += 1

    out = ROOT / "scripts" / "verify_client_fixes_results.json"
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"results_json={out}")
    print(f"summary={'PASS' if failed == 0 else 'FAIL'} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
