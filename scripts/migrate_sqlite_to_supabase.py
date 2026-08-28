#!/usr/bin/env python3
"""
Migrate SQLite (data/jakkash.db) → Supabase PostgreSQL (SUPABASE_DB_URL).

Usage:
  .\\.venv\\Scripts\\python.exe scripts/migrate_sqlite_to_supabase.py --dry-run
  .\\.venv\\Scripts\\python.exe scripts/migrate_sqlite_to_supabase.py
  .\\.venv\\Scripts\\python.exe scripts/migrate_sqlite_to_supabase.py --replace

Product aliases:
  reviews     → testimonials + review_comments
  seller_info → seller_profiles
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

DEFAULT_SQLITE = ROOT / "data" / "jakkash.db"

# Insert order respects FK dependencies. IDs are preserved so remaps stay 1:1.
TABLE_PLAN: list[dict[str, Any]] = [
    {
        "label": "admins",
        "sqlite": "admins",
        "postgres": "admins",
        "columns": [
            "id",
            "username",
            "email",
            "password_hash",
            "full_name",
            "role",
            "permissions_json",
            "phone",
            "phone_verified",
            "require_otp",
            "mobile_otp_enabled",
            "mobile_otp_hash",
            "mobile_otp_expires_at",
            "mobile_otp_sent_at",
            "totp_enabled",
            "totp_secret",
            "last_otp_verified_at",
            "created_by_admin_id",
            "password_reset_failed_attempts",
            "password_reset_locked_until",
            "is_active",
            "created_at",
        ],
        "json_cols": {"permissions_json"},
        "bool_cols": {
            "phone_verified",
            "require_otp",
            "mobile_otp_enabled",
            "totp_enabled",
            "is_active",
        },
        "ts_cols": {
            "mobile_otp_expires_at",
            "mobile_otp_sent_at",
            "last_otp_verified_at",
            "password_reset_locked_until",
            "created_at",
        },
    },
    {
        "label": "properties",
        "sqlite": "properties",
        "postgres": "properties",
        "columns": [
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
            "owner_admin_id",
            "creation_source",
            "block_wing",
            "unit_number",
            "listing_intent",
            "seller_type",
            "created_at",
            "updated_at",
        ],
        "json_cols": {"amenities"},
        "bool_cols": {"is_featured"},
        "ts_cols": {"created_at", "updated_at"},
    },
    {
        "label": "property_images",
        "sqlite": "property_images",
        "postgres": "property_images",
        "columns": [
            "id",
            "property_id",
            "file_path",
            "sort_order",
            "is_primary",
            "uploaded_at",
        ],
        "json_cols": set(),
        "bool_cols": {"is_primary"},
        "ts_cols": {"uploaded_at"},
    },
    {
        "label": "property_videos",
        "sqlite": "property_videos",
        "postgres": "property_videos",
        "columns": [
            "id",
            "property_id",
            "file_path",
            "title",
            "sort_order",
            "uploaded_at",
        ],
        "json_cols": set(),
        "bool_cols": set(),
        "ts_cols": {"uploaded_at"},
    },
    {
        "label": "inquiries",
        "sqlite": "inquiries",
        "postgres": "inquiries",
        "columns": [
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
        ],
        "json_cols": set(),
        "bool_cols": set(),
        "ts_cols": {"created_at", "updated_at"},
    },
    {
        "label": "leads",
        "sqlite": "leads",
        "postgres": "leads",
        "columns": [
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
            "follow_up_date",
            "is_urgent",
            "whatsapp_clicks",
            "call_clicks",
            "properties_viewed",
            "time_on_site_sec",
            "saved_count",
            "inquiry_date",
            "last_contacted_at",
            "created_at",
            "updated_at",
        ],
        "json_cols": set(),
        "bool_cols": {"is_urgent"},
        "ts_cols": {
            "follow_up_date",
            "inquiry_date",
            "last_contacted_at",
            "created_at",
            "updated_at",
        },
    },
    {
        "label": "reviews(testimonials)",
        "sqlite": "testimonials",
        "postgres": "testimonials",
        "columns": [
            "id",
            "client_name",
            "client_location",
            "review_text",
            "rating",
            "is_active",
            "created_at",
        ],
        "json_cols": set(),
        "bool_cols": {"is_active"},
        "ts_cols": {"created_at"},
    },
    {
        "label": "reviews(review_comments)",
        "sqlite": "review_comments",
        "postgres": "review_comments",
        "columns": [
            "id",
            "testimonial_id",
            "commenter_name",
            "commenter_email",
            "comment_text",
            "is_active",
            "admin_id",
            "created_at",
        ],
        "json_cols": set(),
        "bool_cols": {"is_active"},
        "ts_cols": {"created_at"},
    },
    {
        "label": "seller_info(seller_profiles)",
        "sqlite": "seller_profiles",
        "postgres": "seller_profiles",
        "columns": [
            "id",
            "full_name",
            "mobile",
            "email",
            "address",
            "tags_text",
            "notes",
            "created_by_admin_id",
            "created_at",
            "updated_at",
        ],
        "json_cols": set(),  # tags stay TEXT; tags_text→optional JSON handled below
        "bool_cols": set(),
        "ts_cols": {"created_at", "updated_at"},
        "tags_from": "tags_text",
    },
    {
        "label": "customer_visits",
        "sqlite": "customer_visits",
        "postgres": "customer_visits",
        "columns": [
            "id",
            "visit_date",
            "client_name",
            "client_address",
            "client_contact",
            "client_requirement",
            "property_id",
            "property_ids",
            "executive_admin_id",
            "executive_name",
            "executive_address",
            "executive_contact",
            "customer_signature_label",
            "executive_signature_label",
            "customer_signature_data",
            "executive_signature_data",
            "created_by_admin_id",
            "created_at",
            "updated_at",
        ],
        "json_cols": {"property_ids"},
        "bool_cols": set(),
        "ts_cols": {"created_at", "updated_at"},
        "date_cols": {"visit_date"},
    },
]

TRUNCATE_ORDER = [
    "review_comments",
    "testimonials",
    "customer_visits",
    "seller_profiles",
    "leads",
    "inquiries",
    "property_images",
    "property_videos",
    "properties",
    "admins",
]


def _as_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(int(value))
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "on", "t"}:
        return True
    if s in {"0", "false", "no", "off", "f"}:
        return False
    return None


def _parse_jsonish(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    text = str(value).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Comma-separated fallback (amenities / tags)
        if "," in text:
            return [part.strip() for part in text.split(",") if part.strip()]
        return text


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    text = str(value).strip().replace("T", " ")
    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(text[:26], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        # fromisoformat handles many ISO forms
        cleaned = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    dt = _parse_ts(value)
    return dt.date() if dt else None


def open_sqlite(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"SQLite database not found: {path}")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def sqlite_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(r["name"]) for r in rows}


def fetch_rows(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return list(conn.execute(f"SELECT * FROM {table}"))


def transform_row(plan: dict[str, Any], raw: sqlite3.Row, available: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for col in plan["columns"]:
        if col not in available:
            continue
        value = raw[col]
        if col in plan.get("json_cols", set()):
            out[col] = _parse_jsonish(value)
        elif col in plan.get("bool_cols", set()):
            out[col] = _as_bool(value)
        elif col in plan.get("date_cols", set()):
            out[col] = _parse_date(value)
        elif col in plan.get("ts_cols", set()):
            out[col] = _parse_ts(value)
        else:
            out[col] = value

    # seller tags: keep tags_text string; normalize list-like values
    tags_from = plan.get("tags_from")
    if tags_from and tags_from in available and tags_from in out:
        parsed = _parse_jsonish(raw[tags_from])
        if isinstance(parsed, list):
            out[tags_from] = ", ".join(str(x) for x in parsed)
        elif parsed is None:
            out[tags_from] = None
        else:
            out[tags_from] = str(raw[tags_from] or "")

    return out


def _pg_adapt_row(plan: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    from psycopg2.extras import Json

    adapted = dict(row)
    for col in plan.get("json_cols", set()):
        if col in adapted and adapted[col] is not None and not isinstance(
            adapted[col], Json
        ):
            adapted[col] = Json(adapted[col])
    return adapted

def count_sqlite(conn: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for plan in TABLE_PLAN:
        table = plan["sqlite"]
        try:
            counts[plan["label"]] = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]
        except sqlite3.Error:
            counts[plan["label"]] = -1
    return counts


def reset_sequences(pg_conn, tables: list[str]) -> None:
    cur = pg_conn.cursor()
    for table in tables:
        cur.execute(
            f"""
            SELECT setval(
              pg_get_serial_sequence(%s, 'id'),
              COALESCE((SELECT MAX(id) FROM {table}), 1),
              true
            )
            """,
            (table,),
        )
    pg_conn.commit()
    cur.close()


def truncate_tables(pg_conn) -> None:
    cur = pg_conn.cursor()
    cur.execute(
        "TRUNCATE TABLE "
        + ", ".join(TRUNCATE_ORDER)
        + " RESTART IDENTITY CASCADE"
    )
    pg_conn.commit()
    cur.close()


def batch_upsert(pg_conn, plan: dict[str, Any], rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    adapted = [_pg_adapt_row(plan, r) for r in rows]
    cols = list(adapted[0].keys())
    col_sql = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    # Preserve IDs; skip duplicates on re-run
    conflict = "ON CONFLICT (id) DO NOTHING"
    sql = f"INSERT INTO {plan['postgres']} ({col_sql}) VALUES ({placeholders}) {conflict}"
    values = [tuple(r[c] for c in cols) for r in adapted]
    cur = pg_conn.cursor()
    cur.executemany(sql, values)
    pg_conn.commit()
    cur.close()
    return len(values)

def filter_orphan_fks(prepared: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    """Sanitize child rows: drop required FK orphans; null optional FK orphans."""
    property_ids = {r["id"] for r in prepared.get("properties", []) if r.get("id") is not None}
    inquiry_ids = {r["id"] for r in prepared.get("inquiries", []) if r.get("id") is not None}
    admin_ids = {r["id"] for r in prepared.get("admins", []) if r.get("id") is not None}
    testimonial_ids = {r["id"] for r in prepared.get("reviews(testimonials)", []) if r.get("id") is not None}
    skipped: dict[str, int] = {}

    def _drop_missing(label: str, rows: list[dict[str, Any]], col: str, allowed: set) -> list[dict[str, Any]]:
        kept, drop = [], 0
        for row in rows:
            val = row.get(col)
            if val is not None and allowed and val not in allowed:
                drop += 1
                continue
            kept.append(row)
        if drop:
            skipped[label] = skipped.get(label, 0) + drop
        return kept

    def _nullify_optional(rows: list[dict[str, Any]], col: str, allowed: set) -> None:
        for row in rows:
            val = row.get(col)
            if val is not None and allowed and val not in allowed:
                row[col] = None

    prepared["property_images"] = _drop_missing(
        "property_images", prepared.get("property_images", []), "property_id", property_ids
    )
    prepared["property_videos"] = _drop_missing(
        "property_videos", prepared.get("property_videos", []), "property_id", property_ids
    )

    inquiries = prepared.get("inquiries", [])
    _nullify_optional(inquiries, "property_id", property_ids)
    prepared["inquiries"] = inquiries

    leads = prepared.get("leads", [])
    _nullify_optional(leads, "property_id", property_ids)
    _nullify_optional(leads, "inquiry_id", inquiry_ids)
    prepared["leads"] = leads

    comments = prepared.get("reviews(review_comments)", [])
    _nullify_optional(comments, "admin_id", admin_ids)
    prepared["reviews(review_comments)"] = _drop_missing(
        "reviews(review_comments)", comments, "testimonial_id", testimonial_ids
    )

    visits = prepared.get("customer_visits", [])
    _nullify_optional(visits, "property_id", property_ids)
    _nullify_optional(visits, "executive_admin_id", admin_ids)
    _nullify_optional(visits, "created_by_admin_id", admin_ids)
    prepared["customer_visits"] = visits

    sellers = prepared.get("seller_info(seller_profiles)", [])
    _nullify_optional(sellers, "created_by_admin_id", admin_ids)
    prepared["seller_info(seller_profiles)"] = sellers

    return skipped


def migrate(sqlite_path: Path, dry_run: bool, replace: bool) -> dict[str, Any]:
    report: dict[str, Any] = {
        "sqlite_path": str(sqlite_path),
        "dry_run": dry_run,
        "replace": replace,
        "tables": {},
        "ok": False,
        "error": None,
    }

    sq = open_sqlite(sqlite_path)
    try:
        sqlite_counts = count_sqlite(sq)
        report["sqlite_counts"] = sqlite_counts

        prepared: dict[str, list[dict[str, Any]]] = {}
        for plan in TABLE_PLAN:
            table = plan["sqlite"]
            try:
                available = sqlite_columns(sq, table)
            except sqlite3.Error as exc:
                report["tables"][plan["label"]] = {
                    "sqlite": 0,
                    "prepared": 0,
                    "error": str(exc),
                }
                continue
            raw_rows = fetch_rows(sq, table)
            transformed = [transform_row(plan, row, available) for row in raw_rows]
            prepared[plan["label"]] = transformed
            report["tables"][plan["label"]] = {
                "sqlite": len(raw_rows),
                "prepared": len(transformed),
                "postgres_table": plan["postgres"],
                "sample_keys": list(transformed[0].keys()) if transformed else [],
            }

        skipped = filter_orphan_fks(prepared)
        if skipped:
            report["orphans_skipped"] = skipped
            for plan in TABLE_PLAN:
                label = plan["label"]
                if label in prepared:
                    report["tables"][label]["prepared"] = len(prepared[label])

        if dry_run:
            report["ok"] = True
            report["message"] = "Dry-run only - no rows written to Supabase."
            return report

        db_url = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
        if not db_url.startswith("postgres"):
            report["error"] = (
                "SUPABASE_DB_URL is missing. Paste the Postgres URI from "
                "Supabase > Project Settings > Database, then re-run without --dry-run."
            )
            return report

        import psycopg2

        pg = psycopg2.connect(db_url)
        try:
            if replace:
                truncate_tables(pg)

            migrated = 0
            for plan in TABLE_PLAN:
                label = plan["label"]
                rows = prepared.get(label) or []
                written = batch_upsert(pg, plan, rows)
                report["tables"][label]["written"] = written
                migrated += written

            reset_sequences(
                pg,
                [p["postgres"] for p in TABLE_PLAN],
            )
            report["migrated_row_total"] = migrated
            report["ok"] = True
            report["message"] = "Migration completed."
        finally:
            pg.close()
    except Exception as exc:
        report["error"] = str(exc)
        report["ok"] = False
    finally:
        sq.close()

    return report


def print_report(report: dict[str, Any]) -> None:
    print("=" * 60)
    print("SQLite -> Supabase migration")
    print("=" * 60)
    print(f"SQLite:  {report.get('sqlite_path')}")
    print(f"Mode:    {'DRY-RUN' if report.get('dry_run') else 'LIVE'}")
    if report.get("replace"):
        print("Replace: TRUNCATE CASCADE before insert")
    print()
    print(f"{'Table':<32} {'SQLite':>8} {'Prepared':>10} {'Written':>10}")
    print("-" * 64)
    for plan in TABLE_PLAN:
        label = plan["label"]
        info = report.get("tables", {}).get(label, {})
        written = info.get("written", "-")
        print(
            f"{label:<32} {info.get('sqlite', 0):>8} "
            f"{info.get('prepared', 0):>10} {written:>10}"
        )
    print("-" * 64)
    if report.get("migrated_row_total") is not None:
        print(f"Total written (attempted): {report['migrated_row_total']}")
    if report.get("message"):
        print(report["message"])
    if report.get("error"):
        print(f"ERROR: {report['error']}")
    print(f"Status: {'OK' if report.get('ok') else 'FAILED'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Transform and count only; do not write to Postgres",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="TRUNCATE migrated tables (CASCADE) before insert",
    )
    parser.add_argument(
        "--sqlite",
        type=Path,
        default=DEFAULT_SQLITE,
        help=f"Path to SQLite DB (default: {DEFAULT_SQLITE})",
    )
    args = parser.parse_args()

    report = migrate(args.sqlite, dry_run=args.dry_run, replace=args.replace)
    print_report(report)

    # Machine-readable sidecar for vault logging
    out_path = ROOT / "scripts" / "_last_migration_report.json"
    try:
        serializable = json.loads(json.dumps(report, default=str))
        out_path.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        print(f"Report JSON: {out_path}")
    except Exception:
        pass

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
