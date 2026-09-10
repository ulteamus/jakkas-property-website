"""Dump Tokyo cloud data to JSON for Mumbai seed (uses local .env Tokyo URL)."""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

import psycopg2
import psycopg2.extras

TABLES = [
    "admins",
    "properties",
    "property_images",
    "property_videos",
    "property_documents",
    "inquiries",
    "owner_submissions",
    "leads",
    "lead_notes",
    "saved_properties",
    "property_views",
    "visitors",
    "visitor_events",
    "search_analytics",
    "area_demand",
    "testimonials",
    "review_comments",
    "seller_profiles",
    "customer_visits",
    "activity_logs",
]

OUT = ROOT / "scripts" / "_mumbai_seed_data.json"


def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, UUID):
        return str(o)
    if isinstance(o, memoryview):
        return bytes(o).hex()
    if isinstance(o, bytes):
        return o.hex()
    raise TypeError(type(o).__name__)


def main() -> int:
    url = (os.getenv("SUPABASE_DB_URL") or "").strip()
    if not url.startswith("postgres"):
        raise SystemExit("SUPABASE_DB_URL missing")
    conn = psycopg2.connect(url, connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    payload = {}
    for table in TABLES:
        cur.execute(f"SELECT * FROM {table} ORDER BY 1")
        rows = [dict(r) for r in cur.fetchall()]
        payload[table] = rows
        print(f"{table}: {len(rows)}")
    conn.close()
    OUT.write_text(json.dumps(payload, default=_json_default), encoding="utf-8")
    print("wrote", OUT, "bytes", OUT.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
