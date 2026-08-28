"""Flask test-client smoke tests for public, auth, API, and static asset routes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from app import create_app


# (method, path, acceptable_statuses, note)
CASES = [
    ("GET", "/", {200}, "Homepage"),
    ("GET", "/properties", {200}, "Listing grid"),
    ("GET", "/contact", {200}, "Contact"),
    ("GET", "/about", {200}, "About"),
    ("GET", "/static/uploads/hero-fallback.jpg", {200}, "Hero fallback asset"),
    ("GET", "/admin/login", {200}, "Admin login"),
    ("GET", "/login", {404, 302, 301}, "Public /login (may be absent — expect 404)"),
    ("GET", "/api/properties", {200}, "API property list"),
]


def _has_undefined_error(body: str) -> bool:
    markers = (
        "UndefinedError",
        "is undefined",
        "jinja2.exceptions.UndefinedError",
        "home_stats",
    )
    # Only flag if it looks like an error page, not normal content mentioning home_stats
    lower = (body or "").lower()
    if "traceback" in lower or "undefinederror" in lower:
        return True
    if "is undefined" in lower:
        return True
    return False


def main():
    app = create_app()
    client = app.test_client()
    results = []
    failed = 0

    for method, path, ok_statuses, note in CASES:
        try:
            resp = client.open(path, method=method)
            status = resp.status_code
            body = ""
            try:
                body = resp.get_data(as_text=True) or ""
            except Exception:
                body = ""
            undefined = _has_undefined_error(body)
            ok = status in ok_statuses and not undefined
            if not ok:
                failed += 1
            results.append(
                {
                    "endpoint": path,
                    "method": method,
                    "status": status,
                    "ok": ok,
                    "notes": note
                    + ("" if not undefined else " | UndefinedError in body")
                    + ("" if status in ok_statuses else f" | expected {sorted(ok_statuses)}"),
                }
            )
            flag = "PASS" if ok else "FAIL"
            print(f"{flag} {method} {path} -> {status} ({note})")
        except Exception as exc:
            failed += 1
            results.append(
                {
                    "endpoint": path,
                    "method": method,
                    "status": None,
                    "ok": False,
                    "notes": f"{note} | exception: {type(exc).__name__}: {exc}",
                }
            )
            print(f"FAIL {method} {path} -> EXCEPTION {exc}")

    out_path = ROOT / "scripts" / "smoke_test_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"results_json={out_path}")
    print(f"summary_passed={len(results) - failed}/{len(results)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
