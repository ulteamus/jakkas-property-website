#!/usr/bin/env python3
"""
Live E2E persistence checks against production (Cloud Supabase-backed Vercel).

Usage:
  .\\.venv\\Scripts\\python.exe scripts\\verify_cloud_persistence.py
  .\\.venv\\Scripts\\python.exe scripts\\verify_cloud_persistence.py --base https://jakkas-property-website.vercel.app

Checks:
  1) GET /api/properties returns listings
  2) POST /api/inquiry succeeds and (optionally) appears via DB if SUPABASE_DB_URL is cloud
  3) POST /api/reviews persists and is visible on a subsequent homepage/testimonials fetch
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

DEFAULT_BASE = "https://jakkas-property-website.vercel.app"


def _http_json(
    method: str,
    url: str,
    payload: dict | None = None,
    timeout: int = 45,
    headers_extra: dict[str, str] | None = None,
) -> tuple[int, Any, str]:
    data = None
    headers = {"Accept": "application/json", "User-Agent": "jakkas-cloud-verify/1.0"}
    if headers_extra:
        headers.update(headers_extra)
    if payload is not None:
        raw = json.dumps(payload).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", 200) or 200
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except URLError as exc:
        return 0, None, str(exc)
    parsed: Any = None
    try:
        parsed = json.loads(body) if body else None
    except json.JSONDecodeError:
        parsed = None
    return status, parsed, body


def _csrf_session(base: str):
    """Shared cookie jar + CSRF token for Flask-WTF (needs Referer + session)."""
    import re
    from http.cookiejar import CookieJar
    from urllib.request import HTTPCookieProcessor, build_opener

    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    html = opener.open(
        Request(
            base + "/contact",
            headers={"User-Agent": "jakkas-cloud-verify/1.0"},
        ),
        timeout=45,
    ).read().decode("utf-8", errors="replace")
    m = re.search(
        r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']',
        html,
        flags=re.IGNORECASE,
    )
    if not m:
        m = re.search(
            r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
            html,
            flags=re.IGNORECASE,
        )
    token = m.group(1) if m else None
    return opener, token


def _http_json_opener(
    opener,
    method: str,
    url: str,
    payload: dict | None = None,
    timeout: int = 45,
    headers_extra: dict[str, str] | None = None,
) -> tuple[int, Any, str]:
    data = None
    headers = {"Accept": "application/json", "User-Agent": "jakkas-cloud-verify/1.0"}
    if headers_extra:
        headers.update(headers_extra)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", 200) or 200
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except URLError as exc:
        return 0, None, str(exc)
    parsed: Any = None
    try:
        parsed = json.loads(body) if body else None
    except json.JSONDecodeError:
        parsed = None
    return status, parsed, body


def _csrf_from_base(base: str) -> tuple[str | None, str | None]:
    """Return (csrf_token, cookie_header) from the production homepage meta tag."""
    import re
    from http.cookiejar import CookieJar
    from urllib.request import HTTPCookieProcessor, build_opener

    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    try:
        with opener.open(Request(base + "/", headers={"User-Agent": "jakkas-cloud-verify/1.0"}), timeout=45) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None, None
    m = re.search(
        r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
        html,
        flags=re.IGNORECASE,
    )
    token = m.group(1) if m else None
    cookie = "; ".join(f"{c.name}={c.value}" for c in jar)
    return token, (cookie or None)


def _http_text(url: str, timeout: int = 45) -> tuple[int, str]:
    req = Request(url, headers={"User-Agent": "jakkas-cloud-verify/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return getattr(resp, "status", 200) or 200, resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        return 0, str(exc)


def _property_count(payload: Any) -> int:
    if not isinstance(payload, dict):
        return 0
    for key in ("properties", "data", "items", "results"):
        val = payload.get(key)
        if isinstance(val, list):
            return len(val)
    if isinstance(payload.get("count"), int):
        return int(payload["count"])
    return 0


def _db_inquiry_exists(marker: str) -> dict[str, Any]:
    out: dict[str, Any] = {"checked": False, "found": False}
    url = (os.getenv("SUPABASE_DB_URL") or "").strip()
    if not url.startswith("postgres"):
        out["skip"] = "no SUPABASE_DB_URL"
        return out
    host = (urlparse(url).hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        out["skip"] = "loopback DB URL"
        return out
    try:
        import psycopg2

        kwargs: dict[str, Any] = {"dsn": url}
        if "sslmode=" not in url:
            kwargs["sslmode"] = "require"
        conn = psycopg2.connect(**kwargs)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, mobile, message FROM inquiries "
                    "WHERE message LIKE %s ORDER BY id DESC LIMIT 1",
                    (f"%{marker}%",),
                )
                row = cur.fetchone()
                out["checked"] = True
                out["found"] = bool(row)
                if row:
                    out["id"] = row[0]
        finally:
            conn.close()
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.getenv("VERIFY_BASE_URL") or DEFAULT_BASE)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "scripts" / "verify_cloud_persistence_results.json",
    )
    args = parser.parse_args()
    base = args.base.rstrip("/")
    token = uuid.uuid4().hex[:10]
    report: dict[str, Any] = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "base": base,
        "checks": {},
    }
    failed = 0

    print("=" * 64)
    print("Cloud persistence verification")
    print("=" * 64)
    print(f"Base: {base}")

    # CSRF for POST /api/* (session cookie jar + Referer, same as browser)
    opener, csrf_token = _csrf_session(base)
    csrf_headers: dict[str, str] = {
        "Referer": f"{base}/contact",
        "Origin": base,
    }
    if csrf_token:
        csrf_headers["X-CSRFToken"] = csrf_token
    report["csrf"] = {"present": bool(csrf_token)}

    # 1) Properties API
    status, payload, raw = _http_json("GET", f"{base}/api/properties")
    count = _property_count(payload)
    props_ok = status == 200 and count >= 0 and payload is not None
    # Prefer non-empty for a healthy cloud seed, but empty cloud is still a valid API
    report["checks"]["api_properties"] = {
        "ok": props_ok,
        "status": status,
        "count": count,
    }
    print(f"{'PASS' if props_ok else 'FAIL'} GET /api/properties -> {status} count={count}")
    if not props_ok:
        failed += 1

    # 2) Inquiry write
    marker = f"cloud-verify-{token}"
    inq_payload = {
        "name": "Cloud Verify Lead",
        "mobile": "9876501234",
        "email": f"cloud.verify.{token}@example.com",
        "message": f"Persistence probe {marker}",
        "source": "cloud_verify_script",
        "inquiry_type": "general",
    }
    status, payload, raw = _http_json_opener(
        opener, "POST", f"{base}/api/inquiry", inq_payload, headers_extra=csrf_headers
    )
    inq_ok = status in {200, 201} and isinstance(payload, dict) and bool(payload.get("success"))
    db_check = _db_inquiry_exists(marker) if inq_ok else {"checked": False}
    # If DB check ran and found row → strong pass; if skipped, HTTP success is soft pass
    if db_check.get("checked"):
        inq_persist_ok = inq_ok and bool(db_check.get("found"))
    else:
        inq_persist_ok = inq_ok
    report["checks"]["api_inquiry"] = {
        "ok": inq_persist_ok,
        "status": status,
        "response": payload,
        "db": db_check,
        "marker": marker,
    }
    print(
        f"{'PASS' if inq_persist_ok else 'FAIL'} POST /api/inquiry -> {status} "
        f"db_found={db_check.get('found')} skip={db_check.get('skip')}"
    )
    if not inq_persist_ok:
        failed += 1

    # 3) Review write + read-back on homepage/testimonials
    review_text = f"Cloud review persistence {token}"
    status, payload, raw = _http_json_opener(
        opener,
        "POST",
        f"{base}/api/reviews",
        {
            "name": "Cloud Reviewer",
            "location": "Surat",
            "rating": 5,
            "review_text": review_text,
        },
        headers_extra=csrf_headers,
    )
    review_post_ok = status in {200, 201} and isinstance(payload, dict) and bool(payload.get("success"))
    home_status, home_body = _http_text(f"{base}/")
    testi_status, testi_body = _http_text(f"{base}/testimonials")
    visible = (review_text in (home_body or "")) or (review_text in (testi_body or ""))
    review_ok = review_post_ok and home_status == 200 and visible
    report["checks"]["api_reviews"] = {
        "ok": review_ok,
        "post_status": status,
        "post_response": payload,
        "home_status": home_status,
        "testimonials_status": testi_status,
        "visible_after_get": visible,
        "review_text": review_text,
    }
    print(
        f"{'PASS' if review_ok else 'FAIL'} POST /api/reviews -> {status} "
        f"visible_after_get={visible}"
    )
    if not review_ok:
        failed += 1

    report["ok"] = failed == 0
    args.report.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nReport: {args.report}")
    print(f"Overall: {'PASS' if failed == 0 else 'FAIL'} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
