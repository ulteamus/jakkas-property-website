"""Shared schema bootstrap helpers — default super-admin on empty databases."""
from __future__ import annotations

import os

from werkzeug.security import generate_password_hash

DEFAULT_BOOTSTRAP_ADMIN_USERNAME = "sam"
DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME = "Sam"
DEFAULT_BOOTSTRAP_ADMIN_EMAIL = "Jakkashproperty@gmail.com"
DEFAULT_BOOTSTRAP_ADMIN_PASSWORD = "admin123"


def resolve_bootstrap_admin_password(explicit: str | None = None) -> str:
    """Resolve bootstrap password; Vercel ephemeral SQLite always gets a known default."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    env_password = (os.getenv("DEFAULT_ADMIN_PASSWORD") or "").strip()
    if env_password:
        return env_password
    if os.getenv("VERCEL"):
        return DEFAULT_BOOTSTRAP_ADMIN_PASSWORD
    if os.getenv("FLASK_ENV", "").strip().lower() == "production":
        raise RuntimeError(
            "DEFAULT_ADMIN_PASSWORD must be configured before bootstrapping admin credentials."
        )
    print(
        "[SECURITY] DEFAULT_ADMIN_PASSWORD not set; using local bootstrap default password."
    )
    return DEFAULT_BOOTSTRAP_ADMIN_PASSWORD


def bootstrap_password_hash(explicit: str | None = None) -> str:
    return generate_password_hash(resolve_bootstrap_admin_password(explicit))


def seed_default_admin_if_empty(cursor) -> bool:
    """Insert default super-admin when admins table is empty. Returns True if inserted."""
    count = cursor.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    if count != 0:
        return False
    cursor.execute(
        """INSERT INTO admins
           (username, email, password_hash, full_name, role, is_active)
           VALUES (?,?,?,?,?,?)""",
        (
            DEFAULT_BOOTSTRAP_ADMIN_USERNAME,
            DEFAULT_BOOTSTRAP_ADMIN_EMAIL,
            bootstrap_password_hash(),
            DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME,
            "super_admin",
            1,
        ),
    )
    return True
