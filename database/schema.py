"""Shared schema bootstrap helpers — default super-admin on empty databases."""
from __future__ import annotations

import logging
import os
import secrets

from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

DEFAULT_BOOTSTRAP_ADMIN_USERNAME = "sam"
DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME = "Sam"
DEFAULT_BOOTSTRAP_ADMIN_EMAIL = "Jakkashproperty@gmail.com"
LOCAL_DEV_BOOTSTRAP_PASSWORD = "admin123"
_DEV_SECRET_LOGGED = False


def _read_admin_initial_password() -> str:
    for name in ("ADMIN_INITIAL_PASSWORD", "DEFAULT_ADMIN_PASSWORD"):
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def _is_local_dev() -> bool:
    if os.getenv("FLASK_ENV", "").strip().lower() == "development":
        return True
    for name in ("DEBUG", "FLASK_DEBUG"):
        if os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}:
            return True
    return False


def _is_vercel_production() -> bool:
    return bool(os.getenv("VERCEL"))


def resolve_bootstrap_admin_password(explicit: str | None = None) -> str:
    """Resolve bootstrap password — never returns admin123 on Vercel without explicit env."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    env_password = _read_admin_initial_password()
    if env_password:
        return env_password
    if _is_vercel_production():
        raise RuntimeError(
            "ADMIN_INITIAL_PASSWORD must be set for admin bootstrap on Vercel. "
            "Configure it in project environment variables before deploy."
        )
    if _is_local_dev():
        global _DEV_SECRET_LOGGED
        if not _DEV_SECRET_LOGGED:
            logger.warning(
                "[SECURITY] ADMIN_INITIAL_PASSWORD not set; using local dev bootstrap password."
            )
            _DEV_SECRET_LOGGED = True
        return LOCAL_DEV_BOOTSTRAP_PASSWORD
    if os.getenv("FLASK_ENV", "").strip().lower() == "production":
        raise RuntimeError(
            "ADMIN_INITIAL_PASSWORD must be configured before bootstrapping admin credentials."
        )
    logger.warning(
        "[SECURITY] ADMIN_INITIAL_PASSWORD not set; using local dev bootstrap password."
    )
    return LOCAL_DEV_BOOTSTRAP_PASSWORD


def resolve_bootstrap_admin_password_for_seed() -> tuple[str, bool]:
    """Return (password, used_random). On Vercel without env, generates a one-time random secret."""
    env_password = _read_admin_initial_password()
    if env_password:
        return env_password, False
    if _is_vercel_production():
        random_pw = secrets.token_urlsafe(24)
        logger.warning(
            "[SECURITY] ADMIN_INITIAL_PASSWORD unset on Vercel — seeded admin '%s' with a "
            "one-time random password. Set ADMIN_INITIAL_PASSWORD in Vercel env and rotate "
            "via scripts/admin_credentials_audit.py.",
            DEFAULT_BOOTSTRAP_ADMIN_USERNAME,
        )
        return random_pw, True
    return resolve_bootstrap_admin_password(), False


def bootstrap_password_hash(explicit: str | None = None) -> str:
    return generate_password_hash(resolve_bootstrap_admin_password(explicit))


def seed_default_admin_if_empty(cursor) -> bool:
    """Insert default super-admin when admins table is empty. Returns True if inserted."""
    count = cursor.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    if count != 0:
        return False
    password, _random = resolve_bootstrap_admin_password_for_seed()
    cursor.execute(
        """INSERT INTO admins
           (username, email, password_hash, full_name, role, is_active)
           VALUES (?,?,?,?,?,?)""",
        (
            DEFAULT_BOOTSTRAP_ADMIN_USERNAME,
            DEFAULT_BOOTSTRAP_ADMIN_EMAIL,
            generate_password_hash(password),
            DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME,
            "super_admin",
            1,
        ),
    )
    return True
