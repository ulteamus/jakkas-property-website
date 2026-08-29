"""List admins and reset primary bootstrap password (sam or admin)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv(ROOT / ".env", override=False)


def list_admins() -> list[dict]:
    from database.db import query_all

    return query_all(
        "SELECT id, username, email, role, is_active FROM admins ORDER BY id"
    )


def reset_password(username: str, plain: str) -> bool:
    from database.db import execute, query_one

    row = query_one(
        "SELECT id, username FROM admins WHERE LOWER(username)=LOWER(%s)",
        (username,),
    )
    if not row:
        return False
    execute(
        "UPDATE admins SET password_hash=%s WHERE id=%s",
        (generate_password_hash(plain), row["id"]),
    )
    return True


def pick_target(admins: list[dict]) -> str | None:
    names = {a["username"].lower(): a["username"] for a in admins}
    for candidate in ("sam", "admin"):
        if candidate in names:
            return names[candidate]
    return admins[0]["username"] if admins else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit admins and reset bootstrap password")
    parser.add_argument("--password", default="admin123", help="New plaintext password")
    parser.add_argument("--username", default="", help="Force username (default: sam or admin)")
    parser.add_argument("--list-only", action="store_true", help="Only list admins")
    args = parser.parse_args()

    from app import create_app

    app = create_app()
    with app.app_context():
        from database.db import use_postgres, use_sqlite

        backend = "postgres" if use_postgres() else ("sqlite" if use_sqlite() else "mysql")
        print(f"backend={backend}")

        admins = list_admins()
        if not admins:
            from models.admin import Admin

            Admin.ensure_default()
            admins = list_admins()
        if not admins:
            print("No admins found.")
            return 1

        print("admins:")
        for a in admins:
            print(
                f"  id={a['id']} username={a['username']} email={a.get('email')} "
                f"role={a.get('role')} active={a.get('is_active')}"
            )

        if args.list_only:
            return 0

        target = args.username.strip() or pick_target(admins)
        if not target:
            print("No target admin to reset.")
            return 1

        if not reset_password(target, args.password):
            print(f"Reset failed: {target!r} not found.")
            return 1

        print(f"reset_ok username={target} password={args.password}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
