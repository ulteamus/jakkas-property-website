#!/usr/bin/env python3
"""E2E: inquiry/lead API pipeline + admin session CRUD against live PostgreSQL."""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)


def _csrf_from_html(html: str) -> str | None:
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html or "")
    return m.group(1) if m else None


def _login_admin(client) -> bool:
    username = os.getenv("E2E_ADMIN_USER", "sam")
    password = os.getenv(
        "DEFAULT_ADMIN_PASSWORD",
        os.getenv("E2E_ADMIN_PASSWORD", "jodika"),
    )
    page = client.get("/admin/login")
    token = _csrf_from_html(page.get_data(as_text=True))
    data = {"username": username, "password": password}
    if token:
        data["csrf_token"] = token
    resp = client.post("/admin/login", data=data, follow_redirects=False)
    return resp.status_code in (302, 303)


def test_inquiry_pipeline(client, property_id: int) -> dict:
    from database.db import query_one

    mobile = f"98765{uuid.uuid4().int % 100000:05d}"[-10:]
    body = {
        "name": "Jay Test",
        "mobile": mobile,
        "property_id": property_id,
        "intent": "buy",
        "message": "E2E inquiry pipeline test",
        "source": "e2e_test",
    }
    resp = client.post(
        "/api/inquiry",
        json=body,
        content_type="application/json",
    )
    step = {"post_status": resp.status_code, "mobile": mobile}
    if resp.status_code != 200:
        step["body"] = resp.get_json(silent=True)
        return {"ok": False, "error": "POST /api/inquiry failed", **step}

    inquiry = query_one(
        "SELECT id, name, mobile, property_id, status, inquiry_type, created_at "
        "FROM inquiries WHERE mobile=%s ORDER BY id DESC LIMIT 1",
        (mobile,),
    )
    lead = query_one(
        "SELECT id, name, mobile, property_id, inquiry_id, status, created_at "
        "FROM leads WHERE mobile=%s ORDER BY id DESC LIMIT 1",
        (mobile,),
    )
    step["inquiry"] = dict(inquiry) if inquiry else None
    step["lead"] = dict(lead) if lead else None
    ok = bool(
        inquiry
        and lead
        and inquiry.get("name") == "Jay Test"
        and inquiry.get("status") == "new"
        and lead.get("inquiry_id") == inquiry.get("id")
        and lead.get("property_id") == property_id
        and inquiry.get("created_at") is not None
    )
    return {"ok": ok, **step}


def test_admin_portal(client, property_id: int) -> dict:
    from database.db import query_one
    from models import property as prop_model

    if not _login_admin(client):
        return {"ok": False, "error": "Admin login failed"}

    routes = {}
    for path in ("/admin/", "/admin/properties", "/admin/leads"):
        r = client.get(path)
        routes[path] = r.status_code
    if any(code >= 400 for code in routes.values()):
        return {"ok": False, "error": "Admin route access failed", "routes": routes}

    prop = prop_model.get_by_id(property_id)
    if not prop:
        return {"ok": False, "error": f"Property {property_id} missing"}

    edit_get = client.get(f"/admin/properties/{property_id}/edit")
    token = _csrf_from_html(edit_get.get_data(as_text=True))
    new_name = f"{prop['property_name']} [E2E]"
    new_price = float(prop["price"]) + 1000

    form = {
        "property_name": new_name,
        "property_type": prop["property_type"],
        "area_name": prop["area_name"],
        "address": prop.get("address") or "Surat",
        "price": str(int(new_price)),
        "bhk": str(prop.get("bhk") or 0),
        "sq_ft": str(prop.get("sq_ft") or 1000),
        "description": prop.get("description") or "E2E update",
        "amenities": "",
        "latitude": str(prop.get("latitude") or 21.1702),
        "longitude": str(prop.get("longitude") or 72.8311),
        "status": prop.get("status") or "available",
        "listing_type": prop.get("listing_type") or "sale",
        "listing_intent": prop.get("listing_intent") or "sell",
        "creation_source": prop.get("creation_source") or "admin",
    }
    if token:
        form["csrf_token"] = token

    post = client.post(f"/admin/properties/{property_id}/edit", data=form, follow_redirects=False)
    updated = query_one(
        "SELECT property_name, price FROM properties WHERE id=%s",
        (property_id,),
    )
    crud_ok = (
        post.status_code in (302, 303)
        and updated
        and updated["property_name"] == new_name
        and float(updated["price"]) == new_price
    )

    # Restore original title/price for cleanliness
    if crud_ok:
        restore = dict(form)
        restore["property_name"] = prop["property_name"]
        restore["price"] = str(int(prop["price"]))
        if token:
            restore["csrf_token"] = token
        client.post(f"/admin/properties/{property_id}/edit", data=restore, follow_redirects=False)

    return {
        "ok": crud_ok,
        "routes": routes,
        "update_post_status": post.status_code,
        "updated_name": updated.get("property_name") if updated else None,
        "updated_price": float(updated["price"]) if updated else None,
        "restored": crud_ok,
    }


def run() -> dict:
    from app import create_app
    from database.db import query_one, use_postgres

    report: dict = {"ok": False, "sections": {}}
    if not use_postgres():
        report["error"] = "PostgreSQL backend required (USE_SQLITE=0 + SUPABASE_DB_URL)"
        return report

    prop = query_one("SELECT id FROM properties ORDER BY id LIMIT 1")
    if not prop:
        report["error"] = "No properties available"
        return report
    pid = prop["id"]
    report["property_id"] = pid

    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    client = app.test_client()

    report["sections"]["inquiry"] = test_inquiry_pipeline(client, pid)
    report["sections"]["admin"] = test_admin_portal(client, pid)
    report["ok"] = all(
        report["sections"][k].get("ok") for k in ("inquiry", "admin")
    )
    return report


def main() -> int:
    report = run()
    out = ROOT / "scripts" / "_last_e2e_pipeline.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    print(f"report={out}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
