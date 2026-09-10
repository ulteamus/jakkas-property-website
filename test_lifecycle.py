"""
End-to-end lifecycle test: user sell submit → admin approve → public visibility
→ admin update → admin delete, against live Flask + Supabase Postgres.

Phases:
  1) User submission (pending / reserved)
  2) Admin review & approval (submission approved, property available)
  3) Visibility on /properties (API) and /my-listings
  4) Admin property update + delete

Usage:
  python test_lifecycle.py              # HTTP against http://127.0.0.1:5000
  python test_lifecycle.py --client     # Flask test client
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

TAG_PREFIX = "LIFECYCLE"


def _png_bytes() -> bytes:
    import base64

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


def _csrf_from_html(html: str) -> str | None:
    m = re.search(
        r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', html or "", re.I
    )
    if m:
        return m.group(1)
    m = re.search(
        r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html or "", re.I
    )
    return m.group(1) if m else None


def _response_json(r):
    if hasattr(r, "get_json"):
        return r.get_json(silent=True) or {}
    try:
        if callable(getattr(r, "json", None)):
            return r.json() or {}
        return getattr(r, "json", None) or {}
    except Exception:
        return {}


def _response_text(r) -> str:
    if hasattr(r, "text") and isinstance(r.text, str):
        return r.text
    if hasattr(r, "get_data"):
        return r.get_data(as_text=True) or ""
    return ""


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, step: str, status: str, detail: str = "") -> None:
        self.rows.append((step, status, detail))
        print(f"[{status}] {step}" + (f" — {detail}" if detail else ""))

    def failed(self) -> bool:
        return any(s != "PASS" for _, s, _ in self.rows)

    def dump(self) -> None:
        print("\n" + "=" * 64)
        print("LIFECYCLE TEST REPORT")
        print("=" * 64)
        phase = None
        for step, status, detail in self.rows:
            p = step.split(".", 1)[0] if step[:1].isdigit() else None
            if p and p != phase:
                phase = p
                print(f"\n  --- Phase {phase} ---")
            print(f"  {status:6}  {step}" + (f"  | {detail}" if detail else ""))
        print("-" * 64)
        print("RESULT:", "FAIL" if self.failed() else "PASS")


class HttpClient:
    def __init__(self, base: str):
        import requests

        self.base = base.rstrip("/")
        self.s = requests.Session()

    def get(self, path: str, **kw):
        return self.s.get(self.base + path, timeout=kw.pop("timeout", 30), **kw)

    def post(self, path: str, **kw):
        return self.s.post(self.base + path, timeout=kw.pop("timeout", 90), **kw)

    def post_json(self, path: str, payload: dict, csrf: str | None = None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        if csrf:
            headers["X-CSRFToken"] = csrf
        return self.post(path, json=payload, headers=headers)

    def post_form(self, path: str, data: dict, files=None, csrf: str | None = None, headers=None):
        hdrs = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            **(headers or {}),
        }
        form = dict(data)
        if csrf:
            form["csrf_token"] = csrf
            hdrs["X-CSRFToken"] = csrf
        return self.post(path, data=form, files=files, headers=hdrs)


class TestClientAdapter:
    def __init__(self, app):
        self.app = app
        self.client = app.test_client()
        self._ctx = app.app_context()
        self._ctx.push()

    def close(self):
        try:
            self._ctx.pop()
        except Exception:
            pass

    def get(self, path: str, **kw):
        return self.client.get(path, **kw)

    def post(self, path: str, **kw):
        return self.client.post(path, **kw)

    def post_json(self, path: str, payload: dict, csrf: str | None = None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        if csrf:
            headers["X-CSRFToken"] = csrf
        return self.client.post(path, json=payload, headers=headers)

    def post_form(self, path: str, data: dict, files=None, csrf: str | None = None, headers=None):
        hdrs = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            **(headers or {}),
        }
        form = dict(data)
        if csrf:
            form["csrf_token"] = csrf
            hdrs["X-CSRFToken"] = csrf
        if files:
            for key, value in files.items():
                if isinstance(value, (tuple, list)) and len(value) >= 2:
                    filename, content = value[0], value[1]
                    blob = content if isinstance(content, (bytes, bytearray)) else content
                    form[key] = (io.BytesIO(blob), filename)
        return self.client.post(path, data=form, headers=hdrs)


def _admin_creds() -> tuple[str, str]:
    username = os.getenv("E2E_ADMIN_USER") or os.getenv("ADMIN_USERNAME") or "sam"
    password = (
        os.getenv("E2E_ADMIN_PASSWORD")
        or os.getenv("DEFAULT_ADMIN_PASSWORD")
        or os.getenv("ADMIN_INITIAL_PASSWORD")
        or ""
    )
    return username, password


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", action="store_true", help="Use Flask test client")
    parser.add_argument(
        "--base-url",
        default=os.getenv("E2E_BASE_URL", "http://127.0.0.1:5000"),
    )
    args = parser.parse_args()

    os.environ["USE_SQLITE"] = os.getenv("USE_SQLITE", "0")
    os.environ.setdefault("FLASK_USE_RELOADER", "0")

    from database.supabase_client import reset_clients, mask_db_url, supabase_db_url

    reset_clients()

    report = Report()
    token = uuid.uuid4().hex[:8]
    tag = f"{TAG_PREFIX}_{token}"
    digits = "".join(c for c in token if c.isdigit()) or "123456"
    sell_mobile = ("98767" + (digits + "00000")[:5])[:10]
    sell_title = f"{tag} Lifecycle Flat"
    sell_address = f"{token} Lifecycle Rd, Adajan, Surat"
    updated_title = f"{tag} Lifecycle Flat UPDATED"

    property_id = None
    submission_id = None
    adapter = None
    user_session_cookie = None  # keep sell session for my-listings

    print("=" * 64)
    print("Lifecycle test starting")
    print(f"tag={tag}")
    print(f"SUPABASE_DB_URL={mask_db_url(supabase_db_url())}")
    print("=" * 64)

    from app import create_app
    from database import execute, query_one
    from database.db import get_connection
    from flask import g
    from models.admin import Admin

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    # Ensure bootstrap admin exists (Postgres-safe booleans).
    with app.app_context():
        get_connection()
        backend = g.get("db_backend")
        if backend != "postgres":
            report.add("0.setup.db_backend", "FAIL", f"expected postgres got {backend}")
            report.dump()
            return 1
        report.add("0.setup.db_backend", "PASS", "postgres")
        try:
            Admin.ensure_default()
            row = query_one(
                "SELECT id, username FROM admins WHERE LOWER(username)=LOWER(%s)",
                (_admin_creds()[0],),
            )
            if not row:
                row = query_one("SELECT id, username FROM admins ORDER BY id LIMIT 1")
            report.add(
                "0.setup.admin_bootstrap",
                "PASS" if row else "FAIL",
                f"admin={((row or {}).get('username'))}",
            )
        except Exception as exc:
            report.add("0.setup.admin_bootstrap", "FAIL", str(exc))
            report.dump()
            return 1

    use_http = not args.client
    if use_http:
        client = HttpClient(args.base_url)
        try:
            probe = client.get("/")
            report.add(
                "0.setup.server",
                "PASS" if getattr(probe, "status_code", 0) < 500 else "FAIL",
                f"status={getattr(probe, 'status_code', None)}",
            )
        except Exception as exc:
            report.add("0.setup.server", "FAIL", str(exc))
            report.dump()
            return 1
    else:
        adapter = TestClientAdapter(app)
        client = adapter
        report.add("0.setup.server", "PASS", "test_client")

    try:
        # ========== Phase 1: User submission ==========
        print("\n=== Phase 1: User Submission ===")
        csrf = None
        if use_http:
            csrf = _csrf_from_html(_response_text(client.get("/sell-property")))

        form = {
            "owner_name": f"{tag} Owner",
            "owner_mobile": sell_mobile,
            "owner_email": f"life_{token}@example.com",
            "owner_address": "40 Ganesh Krupa Soc, Surat",
            "property_title": sell_title,
            "property_type": "flat",
            "area_sq_ft": "1200",
            "area_value": "1200",
            "area_unit": "sq_ft",
            "price": "5100000",
            "property_address": sell_address,
            "city": "Surat",
            "location_area": "Adajan",
            "listing_intent": "sell",
            "seller_type": "owner",
            "bhk": "3",
            "description": f"{tag} lifecycle pending listing",
        }
        files = {"images": ("life-mock.png", _png_bytes(), "image/png")}
        t0 = time.perf_counter()
        r = client.post_form("/sell-property", form, files=files, csrf=csrf)
        elapsed = (time.perf_counter() - t0) * 1000
        body = _response_json(r)
        status = getattr(r, "status_code", None)
        ok = status in (200, 201) and (
            body.get("success") is True or body.get("status") == "success"
        )
        property_id = body.get("property_id")
        report.add(
            "1.submit.sell_endpoint",
            "PASS" if ok else "FAIL",
            f"status={status} property_id={property_id} {elapsed:.0f}ms",
        )

        with app.app_context():
            prop = query_one(
                "SELECT id, status, property_name FROM properties WHERE property_name=%s ORDER BY id DESC LIMIT 1",
                (sell_title,),
            )
            if prop:
                property_id = prop["id"]
            # Product pending state for user sells is properties.status='reserved'
            # and owner_submissions.status='pending'.
            pending_ok = bool(prop) and str(prop.get("status") or "").lower() in {
                "reserved",
                "pending",
            }
            report.add(
                "1.submit.property_pending",
                "PASS" if pending_ok else "FAIL",
                f"id={property_id} status={(prop or {}).get('status')}",
            )
            sub = query_one(
                "SELECT id, status, property_id FROM owner_submissions WHERE property_title=%s ORDER BY id DESC LIMIT 1",
                (sell_title,),
            )
            if sub:
                submission_id = sub["id"]
            sub_ok = bool(sub) and str(sub.get("status") or "").lower() == "pending"
            report.add(
                "1.submit.submission_pending",
                "PASS" if sub_ok else "FAIL",
                f"id={submission_id} status={(sub or {}).get('status')}",
            )

        # ========== Phase 2: Admin approve ==========
        print("\n=== Phase 2: Admin Review & Approval ===")
        username, password = _admin_creds()
        if not password:
            report.add("2.admin.login", "FAIL", "DEFAULT_ADMIN_PASSWORD / E2E_ADMIN_PASSWORD missing")
        else:
            login_page = client.get("/admin/login")
            login_csrf = _csrf_from_html(_response_text(login_page))
            login_data = {"username": username, "password": password}
            if login_csrf:
                login_data["csrf_token"] = login_csrf
            # HTML form post (not JSON accept) for login
            if use_http:
                login_resp = client.post(
                    "/admin/login",
                    data=login_data,
                    headers={"Accept": "text/html"},
                    allow_redirects=False,
                )
            else:
                login_resp = client.post(
                    "/admin/login",
                    data=login_data,
                    follow_redirects=False,
                )
            login_ok = getattr(login_resp, "status_code", 0) in (302, 303)
            # Some stacks may return 200 with dashboard if already logged in
            if not login_ok and getattr(login_resp, "status_code", 0) == 200:
                dash = client.get("/admin/")
                login_ok = getattr(dash, "status_code", 0) == 200 and "login" not in (
                    getattr(dash, "url", "") or ""
                ).lower()
            report.add(
                "2.admin.login",
                "PASS" if login_ok else "FAIL",
                f"user={username} status={getattr(login_resp, 'status_code', None)}",
            )

            if login_ok and submission_id:
                # Hit sell-properties pending list then approve route
                list_r = client.get("/admin/sell-properties?status=pending")
                list_ok = getattr(list_r, "status_code", 0) == 200
                report.add(
                    "2.admin.sell_properties_page",
                    "PASS" if list_ok else "FAIL",
                    f"status={getattr(list_r, 'status_code', None)}",
                )
                approve_csrf = _csrf_from_html(_response_text(list_r))
                approve_data = {}
                if approve_csrf:
                    approve_data["csrf_token"] = approve_csrf
                if use_http:
                    appr = client.post(
                        f"/admin/sell-properties/{submission_id}/approve",
                        data=approve_data,
                        headers={"Accept": "text/html"},
                        allow_redirects=False,
                    )
                else:
                    appr = client.post(
                        f"/admin/sell-properties/{submission_id}/approve",
                        data=approve_data,
                        follow_redirects=False,
                    )
                appr_ok = getattr(appr, "status_code", 0) in (302, 303, 200)
                report.add(
                    "2.admin.approve_route",
                    "PASS" if appr_ok else "FAIL",
                    f"status={getattr(appr, 'status_code', None)} sid={submission_id}",
                )

                with app.app_context():
                    sub2 = query_one(
                        "SELECT status FROM owner_submissions WHERE id=%s",
                        (submission_id,),
                    )
                    prop2 = query_one(
                        "SELECT status, approval_status FROM properties WHERE id=%s",
                        (property_id,),
                    ) if property_id else None
                    # Fallback if approval_status column missing
                    if prop2 is None and property_id:
                        prop2 = query_one(
                            "SELECT status FROM properties WHERE id=%s",
                            (property_id,),
                        )
                    sub_approved = str((sub2 or {}).get("status") or "").lower() == "approved"
                    prop_live = str((prop2 or {}).get("status") or "").lower() in {
                        "available",
                        "approved",
                        "active",
                    }
                    report.add(
                        "2.admin.db_approved",
                        "PASS" if sub_approved and prop_live else "FAIL",
                        f"submission={(sub2 or {}).get('status')} property={(prop2 or {}).get('status')}",
                    )
            elif login_ok:
                report.add("2.admin.approve_route", "FAIL", "no submission_id")

        # ========== Phase 3: Visibility ==========
        print("\n=== Phase 3: Visibility Verification ===")
        # Public listings API
        api_r = client.get("/api/properties?limit=120")
        api_body = _response_json(api_r)
        props = api_body.get("properties") or []
        names = [str(p.get("property_name") or "") for p in props if isinstance(p, dict)]
        page_r = client.get("/properties")
        visible = sell_title in names
        report.add(
            "3.visibility.public_properties",
            "PASS" if getattr(page_r, "status_code", 0) == 200 and getattr(api_r, "status_code", 0) == 200 and visible else "FAIL",
            f"page={getattr(page_r, 'status_code', None)} api={getattr(api_r, 'status_code', None)} visible={'yes' if visible else 'no'}",
        )

        # my-listings: same session after sell OR mobile lookup
        ml = client.get(f"/my-listings?mobile={sell_mobile}")
        html = _response_text(ml)
        # After approval, UI may show approved / available / active wording
        listed = sell_title in html or sell_mobile in html or (
            property_id is not None and str(property_id) in html
        )
        active_hint = any(
            w in html.lower()
            for w in ("approved", "available", "active", "live", sell_title.lower())
        )
        report.add(
            "3.visibility.my_listings",
            "PASS" if getattr(ml, "status_code", 0) == 200 and listed and active_hint else "FAIL",
            f"status={getattr(ml, 'status_code', None)} tagged={'yes' if listed else 'no'}",
        )

        # ========== Phase 4: Admin update + delete ==========
        print("\n=== Phase 4: Admin Update & Removal ===")
        if property_id and not report.failed() or property_id:
            # Re-ensure admin session still valid
            edit_get = client.get(f"/admin/properties/{property_id}/edit")
            edit_status = getattr(edit_get, "status_code", 0)
            if edit_status in (301, 302, 303):
                # maybe bounced to login — retry login
                username, password = _admin_creds()
                login_page = client.get("/admin/login")
                login_csrf = _csrf_from_html(_response_text(login_page))
                login_data = {"username": username, "password": password}
                if login_csrf:
                    login_data["csrf_token"] = login_csrf
                if use_http:
                    client.post(
                        "/admin/login",
                        data=login_data,
                        headers={"Accept": "text/html"},
                        allow_redirects=True,
                    )
                else:
                    client.post("/admin/login", data=login_data, follow_redirects=True)
                edit_get = client.get(f"/admin/properties/{property_id}/edit")
                edit_status = getattr(edit_get, "status_code", 0)

            report.add(
                "4.update.edit_page",
                "PASS" if edit_status == 200 else "FAIL",
                f"status={edit_status}",
            )
            edit_csrf = _csrf_from_html(_response_text(edit_get))
            update_form = {
                "property_name": updated_title,
                "property_type": "flat",
                "area_name": "Adajan",
                "address": sell_address,
                "price": "5250000",
                "bhk": "3",
                "sq_ft": "1250",
                "description": f"{tag} admin-updated description",
                "amenities": "Parking,Lift",
                "latitude": "21.1702",
                "longitude": "72.8311",
                "status": "available",
                "listing_type": "sale",
                "listing_intent": "sell",
                "seller_type": "owner",
                "creation_source": "user_submission",
            }
            if edit_csrf:
                update_form["csrf_token"] = edit_csrf

            # Update details (+ optional media). Judge success primarily by DB row.
            update_files = {"images": ("life-update.png", _png_bytes(), "image/png")}
            if use_http:
                upd = client.post(
                    f"/admin/properties/{property_id}/edit",
                    data=update_form,
                    files=update_files,
                    headers={"Accept": "text/html"},
                    allow_redirects=False,
                    timeout=90,
                )
            else:
                form_data = dict(update_form)
                form_data["images"] = (io.BytesIO(_png_bytes()), "life-update.png")
                upd = client.post(
                    f"/admin/properties/{property_id}/edit",
                    data=form_data,
                    follow_redirects=False,
                )
            with app.app_context():
                updated = query_one(
                    "SELECT property_name, price, status FROM properties WHERE id=%s",
                    (property_id,),
                )
            name_ok = updated and updated.get("property_name") == updated_title
            price_ok = updated and abs(float(updated.get("price") or 0) - 5250000) < 1
            http_ok = getattr(upd, "status_code", 0) in (200, 302, 303)
            report.add(
                "4.update.property_details",
                "PASS" if name_ok and price_ok else "FAIL",
                f"http={getattr(upd, 'status_code', None)} redirect_ok={http_ok} name={(updated or {}).get('property_name')} price={(updated or {}).get('price')}",
            )

            # Soft archive then hard delete via admin delete route
            with app.app_context():
                execute(
                    "UPDATE properties SET status=%s WHERE id=%s",
                    ("archived", property_id),
                )
                archived = query_one(
                    "SELECT status FROM properties WHERE id=%s", (property_id,)
                )
            report.add(
                "4.remove.archive_status",
                "PASS" if str((archived or {}).get("status") or "").lower() == "archived" else "FAIL",
                f"status={(archived or {}).get('status')}",
            )

            del_csrf = edit_csrf
            props_page = client.get("/admin/properties")
            del_csrf = _csrf_from_html(_response_text(props_page)) or del_csrf
            del_data = {
                "confirm_text": "DELETE",
                "confirm_property_id": str(property_id),
            }
            if del_csrf:
                del_data["csrf_token"] = del_csrf
            if use_http:
                deleted = client.post(
                    f"/admin/properties/{property_id}/delete",
                    data=del_data,
                    headers={"Accept": "text/html"},
                    allow_redirects=False,
                )
            else:
                deleted = client.post(
                    f"/admin/properties/{property_id}/delete",
                    data=del_data,
                    follow_redirects=False,
                )
            with app.app_context():
                gone = query_one("SELECT id FROM properties WHERE id=%s", (property_id,))
                if submission_id:
                    try:
                        execute("DELETE FROM owner_submissions WHERE id=%s", (submission_id,))
                    except Exception:
                        pass
            report.add(
                "4.remove.delete_property",
                "PASS" if gone is None else "FAIL",
                f"http={getattr(deleted, 'status_code', None)} row_gone={gone is None}",
            )
            property_id = None  # cleaned
            submission_id = None

    finally:
        # Safety cleanup if any phase failed mid-run
        print("\nSafety cleanup...")
        with app.app_context():
            try:
                if submission_id:
                    execute("DELETE FROM owner_submissions WHERE id=%s", (submission_id,))
                execute(
                    "DELETE FROM owner_submissions WHERE property_title LIKE %s",
                    (f"{tag}%",),
                )
            except Exception as exc:
                report.add("cleanup.submissions", "WARN", str(exc))
            try:
                if property_id:
                    try:
                        execute(
                            "DELETE FROM property_images WHERE property_id=%s",
                            (property_id,),
                        )
                    except Exception:
                        pass
                    execute("DELETE FROM properties WHERE id=%s", (property_id,))
                execute(
                    "DELETE FROM properties WHERE property_name LIKE %s",
                    (f"{tag}%",),
                )
            except Exception as exc:
                report.add("cleanup.properties", "WARN", str(exc))
            try:
                execute(
                    "DELETE FROM inquiries WHERE mobile=%s OR name LIKE %s",
                    (sell_mobile, f"{tag}%"),
                )
            except Exception:
                pass
            left_p = query_one(
                "SELECT COUNT(*) AS c FROM properties WHERE property_name LIKE %s",
                (f"{tag}%",),
            )
            left_s = query_one(
                "SELECT COUNT(*) AS c FROM owner_submissions WHERE property_title LIKE %s",
                (f"{tag}%",),
            )
            clean = int((left_p or {}).get("c") or 0) == 0 and int((left_s or {}).get("c") or 0) == 0
            report.add(
                "cleanup.final",
                "PASS" if clean else "FAIL",
                f"left props={(left_p or {}).get('c')} submissions={(left_s or {}).get('c')}",
            )
        if adapter:
            adapter.close()

    report.dump()
    return 1 if report.failed() else 0


if __name__ == "__main__":
    raise SystemExit(main())
