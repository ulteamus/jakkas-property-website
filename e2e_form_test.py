"""
E2E form submission smoke test against live Flask + Supabase Postgres.

Steps:
  1) POST Contact Us -> /api/inquiry (JSON 2xx)
  2) POST Sell Property -> /sell-property (JSON 200/201)
  3) Verify rows in cloud DB (inquiries, owner_submissions, properties)
  4) Hit /my-listings and /properties for live render
  5) Delete tagged test rows

Usage:
  python e2e_form_test.py              # HTTP against http://127.0.0.1:5000
  python e2e_form_test.py --client     # Flask test client (same process/DB)
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

TAG_PREFIX = "E2E_FORM"


def _png_bytes() -> bytes:
    # Minimal valid 1x1 PNG
    import base64

    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )


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
        mark = "PASS" if status == "PASS" else status
        print(f"[{mark}] {step}" + (f" — {detail}" if detail else ""))

    def failed(self) -> bool:
        return any(s != "PASS" for _, s, _ in self.rows)

    def dump(self) -> None:
        print("\n" + "=" * 64)
        print("E2E FORM TEST REPORT")
        print("=" * 64)
        for step, status, detail in self.rows:
            print(f"  {status:6}  {step}" + (f"  | {detail}" if detail else ""))
        print("-" * 64)
        print("RESULT:", "FAIL" if self.failed() else "PASS")


def _csrf_from_html(html: str) -> str | None:
    m = re.search(
        r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']', html, re.I
    )
    if m:
        return m.group(1)
    m = re.search(
        r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html, re.I
    )
    return m.group(1) if m else None


class HttpClient:
    """Thin wrapper over requests.Session for live server."""

    def __init__(self, base: str):
        import requests

        self.base = base.rstrip("/")
        self.s = requests.Session()
        self._requests = requests

    def get(self, path: str):
        return self.s.get(self.base + path, timeout=30)

    def post_json(self, path: str, payload: dict, csrf: str | None = None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        if csrf:
            headers["X-CSRFToken"] = csrf
        return self.s.post(self.base + path, json=payload, headers=headers, timeout=60)

    def post_form(self, path: str, data: dict, files=None, csrf: str | None = None):
        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        form = dict(data)
        if csrf:
            form["csrf_token"] = csrf
            headers["X-CSRFToken"] = csrf
        return self.s.post(
            self.base + path, data=form, files=files, headers=headers, timeout=90
        )


class TestClientAdapter:
    """Flask test_client adapter with same surface as HttpClient."""

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

    def get(self, path: str):
        return self.client.get(path)

    def post_json(self, path: str, payload: dict, csrf: str | None = None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        if csrf:
            headers["X-CSRFToken"] = csrf
        return self.client.post(path, json=payload, headers=headers)

    def post_form(self, path: str, data: dict, files=None, csrf: str | None = None):
        headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }
        form = dict(data)
        if csrf:
            form["csrf_token"] = csrf
            headers["X-CSRFToken"] = csrf
        if files:
            # Map requests-style files into Flask test-client multipart tuples.
            for key, value in files.items():
                if isinstance(value, (tuple, list)) and len(value) >= 2:
                    filename, content = value[0], value[1]
                    form[key] = (io.BytesIO(content if isinstance(content, (bytes, bytearray)) else content), filename)
        return self.client.post(path, data=form, headers=headers)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client",
        action="store_true",
        help="Use Flask test client instead of live HTTP server",
    )
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
    inquiry_id = None
    property_id = None
    submission_id = None
    adapter = None

    print("=" * 64)
    print("E2E form test starting")
    print(f"tag={tag}")
    print(f"SUPABASE_DB_URL={mask_db_url(supabase_db_url())}")
    print("=" * 64)

    from app import create_app
    from database import execute, query_one
    from database.db import get_connection
    from flask import g

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    use_http = not args.client
    if use_http:
        client = HttpClient(args.base_url)
        mode = f"http:{args.base_url}"
        try:
            probe = client.get("/")
            if getattr(probe, "status_code", 0) >= 500:
                report.add("server_probe", "FAIL", f"status={probe.status_code}")
                report.dump()
                return 1
            report.add("server_probe", "PASS", f"status={probe.status_code}")
        except Exception as exc:
            report.add("server_probe", "FAIL", str(exc))
            report.dump()
            return 1
    else:
        adapter = TestClientAdapter(app)
        client = adapter
        mode = "test_client"
    report.add("client_mode", "PASS", mode)

    # Confirm Postgres backend via app context
    with app.app_context():
        get_connection()
        backend = g.get("db_backend")
        if backend != "postgres":
            report.add("db_backend", "FAIL", f"expected postgres got {backend}")
            report.dump()
            return 1
        report.add("db_backend", "PASS", "postgres")

    # Stable 10-digit Indian mobiles unique per run
    digits = "".join(c for c in token if c.isdigit()) or "123456"
    contact_mobile = ("98765" + (digits + "00000")[:5])[:10]
    sell_mobile = ("98766" + (digits + "00000")[:5])[:10]
    contact_name = f"{tag} Contact"
    contact_msg = f"{tag} inquiry message from e2e_form_test"
    sell_title = f"{tag} Sell Flat"
    sell_address = f"{token} {tag} Street, Adajan, Surat"

    try:
        # --- 1) Contact Us ---
        csrf = None
        if use_http:
            r_get = client.get("/contact")
            csrf = _csrf_from_html(_response_text(r_get))
        t0 = time.perf_counter()
        r = client.post_json(
            "/api/inquiry",
            {
                "name": contact_name,
                "mobile": contact_mobile,
                "email": f"e2e_{token}@example.com",
                "message": contact_msg,
                "inquiry_type": "general",
                "source": "e2e_form_test",
            },
            csrf=csrf,
        )
        elapsed = (time.perf_counter() - t0) * 1000
        status = getattr(r, "status_code", None)
        body = _response_json(r)
        ok = status in (200, 201) and bool(body.get("success"))
        report.add(
            "contact_submit",
            "PASS" if ok else "FAIL",
            f"status={status} body={body} {elapsed:.0f}ms",
        )

        with app.app_context():
            row = query_one(
                "SELECT id, name, mobile, message FROM inquiries WHERE name=%s ORDER BY id DESC LIMIT 1",
                (contact_name,),
            )
            if row and row.get("id"):
                inquiry_id = row["id"]
                report.add("contact_db_verify", "PASS", f"inquiries.id={inquiry_id}")
            else:
                report.add("contact_db_verify", "FAIL", "no inquiries row for tag")

        # --- 2) Sell Property ---
        csrf = None
        if use_http:
            r_get = client.get("/sell-property")
            csrf = _csrf_from_html(_response_text(r_get))

        form = {
            "owner_name": f"{tag} Owner",
            "owner_mobile": sell_mobile,
            "owner_email": f"seller_{token}@example.com",
            "owner_address": "40 Ganesh Krupa Soc, Surat",
            "property_title": sell_title,
            "property_type": "flat",
            "area_sq_ft": "1100",
            "area_value": "1100",
            "area_unit": "sq_ft",
            "price": "4500000",
            "property_address": sell_address,
            "city": "Surat",
            "location_area": "Adajan",
            "listing_intent": "sell",
            "seller_type": "owner",
            "bhk": "2",
            "description": f"{tag} sell property e2e description",
        }

        files = {
            "images": ("e2e-mock.png", _png_bytes(), "image/png"),
        }

        t0 = time.perf_counter()
        r = client.post_form("/sell-property", form, files=files, csrf=csrf)
        elapsed = (time.perf_counter() - t0) * 1000
        status = getattr(r, "status_code", None)
        body = _response_json(r)
        ok = status in (200, 201) and (
            body.get("success") is True or body.get("status") == "success"
        )
        property_id = body.get("property_id")
        report.add(
            "sell_submit",
            "PASS" if ok else "FAIL",
            f"status={status} property_id={property_id} body={body} {elapsed:.0f}ms",
        )

        with app.app_context():
            prop = query_one(
                "SELECT id, property_name, status FROM properties WHERE property_name=%s ORDER BY id DESC LIMIT 1",
                (sell_title,),
            )
            if prop and prop.get("id"):
                property_id = prop["id"]
                report.add(
                    "sell_property_db",
                    "PASS",
                    f"properties.id={property_id} status={prop.get('status')}",
                )
            else:
                report.add("sell_property_db", "FAIL", "property row missing")

            sub = query_one(
                "SELECT id, property_id, property_title, status FROM owner_submissions WHERE property_title=%s ORDER BY id DESC LIMIT 1",
                (sell_title,),
            )
            if sub and sub.get("id"):
                submission_id = sub["id"]
                report.add(
                    "sell_submission_db",
                    "PASS",
                    f"owner_submissions.id={submission_id} (product: submissions)",
                )
            else:
                report.add(
                    "sell_submission_db",
                    "FAIL",
                    "owner_submissions row missing (no submissions table; using owner_submissions)",
                )

            # Make listing publicly visible for /properties assert
            if property_id:
                execute(
                    "UPDATE properties SET status='available' WHERE id=%s",
                    (property_id,),
                )

        # --- 3) Frontend routes ---
        # Pass mobile so my-listings can resolve even if session cookie edge-case
        r = client.get(f"/my-listings?mobile={sell_mobile}")
        status = getattr(r, "status_code", None)
        html = _response_text(r)
        listed = (
            sell_title in html
            or sell_mobile in html
            or (property_id is not None and str(property_id) in html)
        )
        ok_route = status == 200 and listed
        report.add(
            "route_my_listings",
            "PASS" if ok_route else "FAIL",
            f"status={status} tagged_visible={'yes' if listed else 'no'}",
        )

        r = client.get("/properties")
        status = getattr(r, "status_code", None)
        html_ok = status == 200
        # Listings page is JS-driven; live data comes from /api/properties
        api_r = client.get("/api/properties?limit=100")
        api_status = getattr(api_r, "status_code", None)
        api_body = _response_json(api_r)
        props = api_body.get("properties") or api_body.get("data") or []
        if isinstance(api_body, list):
            props = api_body
        names = []
        for p in props if isinstance(props, list) else []:
            if isinstance(p, dict):
                names.append(str(p.get("property_name") or p.get("title") or ""))
        shown = sell_title in names or sell_title in _response_text(api_r)
        ok_route = html_ok and api_status == 200 and shown
        report.add(
            "route_properties",
            "PASS" if ok_route else "FAIL",
            f"page={status} api={api_status} title_visible={'yes' if shown else 'no'} count={len(names)}",
        )

    finally:
        # --- 4) Cleanup ---
        print("\nCleaning tagged E2E rows...")
        with app.app_context():
            try:
                if inquiry_id:
                    execute("DELETE FROM inquiries WHERE id=%s", (inquiry_id,))
                execute(
                    "DELETE FROM inquiries WHERE name LIKE %s OR mobile IN (%s,%s)",
                    (f"{tag}%", contact_mobile, sell_mobile),
                )
            except Exception as exc:
                report.add("cleanup_inquiry", "WARN", str(exc))
            try:
                execute(
                    "DELETE FROM leads WHERE mobile IN (%s,%s) OR name LIKE %s",
                    (contact_mobile, sell_mobile, f"{tag}%"),
                )
            except Exception:
                pass
            try:
                if submission_id:
                    execute("DELETE FROM owner_submissions WHERE id=%s", (submission_id,))
                else:
                    execute(
                        "DELETE FROM owner_submissions WHERE property_title LIKE %s",
                        (f"{tag}%",),
                    )
            except Exception as exc:
                report.add("cleanup_submission", "WARN", str(exc))
            try:
                if property_id:
                    try:
                        execute("DELETE FROM property_images WHERE property_id=%s", (property_id,))
                    except Exception:
                        pass
                    try:
                        execute("DELETE FROM property_videos WHERE property_id=%s", (property_id,))
                    except Exception:
                        pass
                    execute("DELETE FROM properties WHERE id=%s", (property_id,))
                else:
                    execute(
                        "DELETE FROM properties WHERE property_name LIKE %s",
                        (f"{tag}%",),
                    )
            except Exception as exc:
                report.add("cleanup_property", "WARN", str(exc))

            left_p = query_one(
                "SELECT COUNT(*) AS c FROM properties WHERE property_name LIKE %s",
                (f"{tag}%",),
            )
            left_i = query_one(
                "SELECT COUNT(*) AS c FROM inquiries WHERE name LIKE %s",
                (f"{tag}%",),
            )
            left_s = query_one(
                "SELECT COUNT(*) AS c FROM owner_submissions WHERE property_title LIKE %s",
                (f"{tag}%",),
            )
            clean = (
                int((left_p or {}).get("c") or 0) == 0
                and int((left_i or {}).get("c") or 0) == 0
                and int((left_s or {}).get("c") or 0) == 0
            )
            report.add(
                "cleanup",
                "PASS" if clean else "FAIL",
                f"left properties={(left_p or {}).get('c')} inquiries={(left_i or {}).get('c')} submissions={(left_s or {}).get('c')}",
            )

        if adapter:
            adapter.close()

    report.dump()
    return 1 if report.failed() else 0


if __name__ == "__main__":
    raise SystemExit(main())
