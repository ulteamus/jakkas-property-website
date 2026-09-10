#!/usr/bin/env python3
"""Seed cloud Supabase via PostgREST using SUPABASE_URL + SUPABASE_KEY."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from database.supabase_client import get_supabase_client, reset_clients  # noqa: E402


def row_dict(r: sqlite3.Row, cols: list[str]) -> dict:
    out = {}
    keys = set(r.keys())
    for c in cols:
        if c not in keys:
            continue
        v = r[c]
        if c in {"is_active", "is_featured", "is_urgent"} and v is not None:
            out[c] = bool(int(v))
        elif c == "amenities" and isinstance(v, str):
            try:
                out[c] = json.loads(v)
            except Exception:
                out[c] = []
        else:
            out[c] = v
    return out


def upsert(table: str, rows: list[dict], on_conflict: str = "id") -> int:
    if not rows:
        return 0
    client = get_supabase_client()
    # Prefer upsert; fall back to insert ignore errors
    resp = (
        client.table(table)
        .upsert(rows, on_conflict=on_conflict)
        .execute()
    )
    data = getattr(resp, "data", None) or []
    return len(data) if data else len(rows)


def main() -> int:
    db = ROOT / "data" / "jakkash.db"
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    reset_clients()

    admin_cols = [
        "id",
        "username",
        "email",
        "password_hash",
        "full_name",
        "role",
        "phone",
        "is_active",
        "created_at",
    ]
    prop_cols = [
        "id",
        "property_name",
        "slug",
        "property_type",
        "area_name",
        "address",
        "price",
        "bhk",
        "sq_ft",
        "description",
        "amenities",
        "latitude",
        "longitude",
        "status",
        "is_featured",
        "listing_type",
        "view_count",
        "primary_image",
        "creation_source",
        "listing_intent",
        "created_at",
        "updated_at",
    ]
    test_cols = [
        "id",
        "client_name",
        "client_location",
        "review_text",
        "rating",
        "is_active",
        "created_at",
    ]
    inq_cols = [
        "id",
        "name",
        "mobile",
        "email",
        "message",
        "property_id",
        "source",
        "status",
        "notes",
        "budget",
        "preferred_location",
        "inquiry_type",
        "created_at",
        "updated_at",
    ]
    lead_cols = [
        "id",
        "name",
        "mobile",
        "email",
        "budget",
        "preferred_area",
        "property_id",
        "inquiry_id",
        "status",
        "lead_score",
        "lead_tier",
        "is_urgent",
        "inquiry_date",
        "created_at",
        "updated_at",
    ]

    report = {}
    for table, cols, sql in [
        ("admins", admin_cols, "SELECT * FROM admins"),
        ("properties", prop_cols, "SELECT * FROM properties"),
        ("testimonials", test_cols, "SELECT * FROM testimonials"),
        ("inquiries", inq_cols, "SELECT * FROM inquiries"),
        ("leads", lead_cols, "SELECT * FROM leads"),
    ]:
        try:
            rows = [row_dict(r, cols) for r in con.execute(sql).fetchall()]
        except sqlite3.Error as exc:
            report[table] = f"skip:{exc}"
            continue
        try:
            n = upsert(table, rows)
            report[table] = n
        except Exception as exc:
            report[table] = f"err:{exc}"
            print(table, "FAILED", exc)
            return 1

    print(json.dumps(report, indent=2))
    # verify counts via REST
    client = get_supabase_client()
    for t in ("properties", "admins", "testimonials", "inquiries", "leads"):
        data = client.table(t).select("id", count="exact").execute()
        print(t, "cloud_count", getattr(data, "count", None), "rows", len(data.data or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
