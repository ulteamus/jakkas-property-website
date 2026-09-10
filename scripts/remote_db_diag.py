"""Verify Flask/psycopg2 reaches remote Supabase and can query core tables."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)


def main() -> int:
    os.environ["USE_SQLITE"] = "0"
    from database.supabase_client import (
        mask_db_url,
        postgres_configured,
        reset_clients,
        supabase_db_url,
        supabase_url,
    )
    from database.db import use_postgres, use_sqlite

    reset_clients()
    print("SUPABASE_URL", supabase_url())
    print("SUPABASE_DB_URL", mask_db_url(supabase_db_url()))
    print("postgres_configured", postgres_configured())
    print("use_postgres", use_postgres())
    print("use_sqlite", use_sqlite())

    from app import create_app

    app = create_app()
    with app.app_context():
        from database import query_all, query_one
        from flask import g
        from database.db import get_connection

        get_connection()
        print("db_backend", g.get("db_backend"))
        row = query_one("SELECT current_database() AS db, current_user AS usr")
        print("session", row)
        for table in ("properties", "testimonials", "reviews", "owner_submissions"):
            try:
                c = query_one(f"SELECT COUNT(*) AS c FROM {table}")
                print(f"count {table}={c.get('c') if c else None}")
            except Exception as exc:
                print(f"count {table} ERR {type(exc).__name__}: {exc}")
                return 1
    print("DIAG_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
