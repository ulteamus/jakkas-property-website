#!/usr/bin/env python3
"""E2E: Supabase Storage upload via storage_service + property_images attach."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

# Minimal 1x1 PNG
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x0e\x00\x00\x00IHDR\x0e\x0e\x08\x02\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e"
    b"\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e\x0e"
    b"\x0e\x0e\x0e\x0eIEND\xaeB`\x82"
)


def _make_png() -> bytes:
    """Valid tiny PNG via Pillow if available, else fallback bytes."""
    try:
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (8, 8), color=(30, 120, 200)).save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return PNG_BYTES


def run() -> dict:
    import requests
    from werkzeug.datastructures import FileStorage

    from app import create_app
    from config import ALLOWED_IMAGE
    from database.db import query_one, use_postgres
    from models import property as prop_model
    from services.storage_service import save_media, supabase_configured

    report: dict = {"ok": False, "steps": []}

    if not use_postgres():
        report["error"] = "USE_SQLITE=1 or SUPABASE_DB_URL missing — Postgres required"
        return report
    if not supabase_configured():
        report["error"] = "Supabase storage credentials not configured"
        return report

    prop = query_one("SELECT id, property_name FROM properties ORDER BY id LIMIT 1")
    if not prop:
        report["error"] = "No properties in PostgreSQL"
        return report
    pid = prop["id"]

    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False

    payload = _make_png()
    fs = FileStorage(
        stream=io.BytesIO(payload),
        filename="e2e-test-upload.png",
        content_type="image/png",
    )

    with app.app_context():
        url = save_media(fs, pid, "images", ALLOWED_IMAGE)
        report["steps"].append({"upload": "ok" if url else "fail", "url": url})
        if not url or not str(url).startswith("http"):
            report["error"] = f"save_media did not return public URL: {url!r}"
            return report

        resp = requests.get(url, timeout=30)
        report["steps"].append({"http_get": resp.status_code})
        if resp.status_code != 200:
            report["error"] = f"Public URL returned HTTP {resp.status_code}"
            return report

        before = query_one(
            "SELECT COUNT(*) AS c FROM property_images WHERE property_id=%s",
            (pid,),
        )["c"]
        prop_model.add_image(pid, url, is_primary=False, sort_order=999)
        row = query_one(
            "SELECT id, file_path FROM property_images WHERE property_id=%s AND file_path=%s",
            (pid, url),
        )
        after = query_one(
            "SELECT COUNT(*) AS c FROM property_images WHERE property_id=%s",
            (pid,),
        )["c"]
        report["steps"].append(
            {
                "property_id": pid,
                "images_before": before,
                "images_after": after,
                "row_id": row["id"] if row else None,
            }
        )
        if not row or after <= before:
            report["error"] = "property_images row not created"
            return report

    report["ok"] = True
    report["message"] = "Storage upload + HTTP 200 + DB attach verified"
    return report


def main() -> int:
    report = run()
    out = ROOT / "scripts" / "_last_storage_e2e.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))
    print(f"report={out}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
