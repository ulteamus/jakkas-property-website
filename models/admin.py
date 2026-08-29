import json
import os
import re
import secrets
from datetime import datetime, timedelta

import pyotp
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from config import COMPANY_NAME, COMPANY_PHONE_RAW
from database import execute, query_all, query_one
from database.db import skip_runtime_ddl, use_sqlite
from database.schema import (
    DEFAULT_BOOTSTRAP_ADMIN_EMAIL,
    DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME,
    DEFAULT_BOOTSTRAP_ADMIN_USERNAME,
    _read_admin_initial_password,
    bootstrap_password_hash,
    resolve_bootstrap_admin_password,
)
from services.mobile_otp import send_mobile_otp_code

ROLE_SUPER_ADMIN = "super_admin"
ROLE_MAIN_ADMIN = "main_admin"
ROLE_MANAGER = "manager"
ROLE_EXECUTIVE = "executive"
ROLE_CALLER = "caller"
ROLE_BROKER = "broker"

ROLE_KEYS = [
    ROLE_SUPER_ADMIN,
    ROLE_MAIN_ADMIN,
    ROLE_MANAGER,
    ROLE_EXECUTIVE,
    ROLE_CALLER,
    ROLE_BROKER,
]

LEGACY_BOOTSTRAP_ADMIN_USERNAME = "admin"

PERMISSION_KEYS = [
    "manage_properties",
    "manage_leads",
    "manage_inquiries",
    "manage_reviews",
    "view_analytics",
    "manage_settings",
    "manage_users",
    "manage_submissions",
    "manage_sellers",
    "manage_customer_visits",
    "view_activity_logs",
    "manage_utilities",
]

ROLE_PRESETS = {
    ROLE_SUPER_ADMIN: list(PERMISSION_KEYS),
    ROLE_MAIN_ADMIN: list(PERMISSION_KEYS),
    ROLE_MANAGER: [
        "manage_properties",
        "manage_leads",
        "manage_inquiries",
        "manage_reviews",
        "view_analytics",
        "manage_submissions",
        "manage_sellers",
        "manage_customer_visits",
    ],
    ROLE_EXECUTIVE: [
        "manage_properties",
        "manage_inquiries",
        "manage_submissions",
        "manage_sellers",
        "manage_customer_visits",
    ],
    ROLE_CALLER: [
        "manage_leads",
        "manage_inquiries",
    ],
    ROLE_BROKER: [
        "manage_properties",
        "manage_leads",
        "manage_inquiries",
    ],
}

EXECUTIVE_ALLOWED_PERMISSIONS = {
    "manage_properties",
    "manage_inquiries",
    "manage_submissions",
    "manage_sellers",
    "manage_customer_visits",
}

BROKER_ALLOWED_PERMISSIONS = {
    "manage_properties",
    "manage_leads",
    "manage_inquiries",
}

ROLE_TITLES = {
    ROLE_SUPER_ADMIN: "Super Admin",
    ROLE_MAIN_ADMIN: "Main Admin",
    ROLE_MANAGER: "Manager",
    ROLE_EXECUTIVE: "Executive",
    ROLE_CALLER: "Caller",
    ROLE_BROKER: "Broker",
}


def role_options_for_ui():
    """Role dropdown + preset cards for /admin/employees."""
    options = [
        {
            "value": role,
            "title": ROLE_TITLES.get(role, role.replace("_", " ").title()),
            "permissions": list(ROLE_PRESETS.get(role, [])),
        }
        for role in ROLE_KEYS
    ]
    if not any(opt["value"] == ROLE_BROKER for opt in options):
        options.append(
            {
                "value": ROLE_BROKER,
                "title": "Broker",
                "permissions": [
                    "manage_properties",
                    "manage_leads",
                    "manage_inquiries",
                ],
            }
        )
    return options


_schema_checked = False
_OTP_EXPIRY_MINUTES = 10
_PASSWORD_RESET_MAX_ATTEMPTS = 5
_PASSWORD_RESET_COOLDOWN_MINUTES = 10


def _normalize_role(value):
    role = (value or "").strip().lower()
    mapping = {
        "admin": ROLE_MAIN_ADMIN,
        "main_admin": ROLE_MAIN_ADMIN,
        "mainadmin": ROLE_MAIN_ADMIN,
        "superadmin": ROLE_SUPER_ADMIN,
        "super_admin": ROLE_SUPER_ADMIN,
        "manager": ROLE_MANAGER,
        "agent": ROLE_EXECUTIVE,
        "employee": ROLE_EXECUTIVE,
        "executive": ROLE_EXECUTIVE,
        "caller": ROLE_CALLER,
        "broker": ROLE_BROKER,
        "agent_broker": ROLE_BROKER,
    }
    normalized = mapping.get(role, role)
    return normalized if normalized in ROLE_KEYS else ROLE_EXECUTIVE


def _now_utc():
    return datetime.utcnow().replace(microsecond=0)


def _to_text_timestamp(dt_obj):
    if not dt_obj:
        return None
    if isinstance(dt_obj, datetime):
        return dt_obj.replace(microsecond=0).isoformat(sep=" ")
    return str(dt_obj)


def _parse_timestamp(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", ""))
    except ValueError:
        return None


def _active_full_admin_count(exclude_admin_id=None):
    sql = "SELECT COUNT(*) AS c FROM admins WHERE role IN (%s,%s) AND is_active=1"
    params = [ROLE_SUPER_ADMIN, ROLE_MAIN_ADMIN]
    if exclude_admin_id is not None:
        sql += " AND id!=%s"
        params.append(exclude_admin_id)
    row = query_one(sql, params)
    return int((row or {}).get("c") or 0)


def _parse_permissions(raw_permissions, role):
    defaults = set(ROLE_PRESETS.get(role, []))
    if raw_permissions is None:
        return defaults
    if isinstance(raw_permissions, (list, tuple, set)):
        cleaned = {str(p).strip() for p in raw_permissions if str(p).strip() in PERMISSION_KEYS}
        return cleaned or defaults
    if not isinstance(raw_permissions, str):
        return defaults
    text = raw_permissions.strip()
    if not text:
        return defaults
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = [p.strip() for p in text.split(",")]
    if isinstance(parsed, dict):
        cleaned = {key for key, enabled in parsed.items() if key in PERMISSION_KEYS and enabled}
    else:
        cleaned = {str(p).strip() for p in parsed if str(p).strip() in PERMISSION_KEYS}
    return cleaned or defaults


def _digits_only(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _serialize_permissions(permission_values):
    filtered = [p for p in PERMISSION_KEYS if p in set(permission_values or [])]
    return json.dumps(filtered)


def _ensure_schema():
    global _schema_checked
    if _schema_checked:
        return
    _schema_checked = True
    if skip_runtime_ddl():
        return

    if use_sqlite():
        _ensure_sqlite_schema()
    else:
        _ensure_mysql_schema()
    _normalize_existing_roles_and_permissions()


def _ensure_sqlite_schema():
    cols = {str(row.get("name", "")).lower() for row in query_all("PRAGMA table_info(admins)")}
    _ensure_sqlite_column(cols, "role", "TEXT DEFAULT 'executive'")
    _ensure_sqlite_column(cols, "permissions_json", "TEXT")
    _ensure_sqlite_column(cols, "phone", "TEXT")
    _ensure_sqlite_column(cols, "phone_verified", "INTEGER DEFAULT 0")
    _ensure_sqlite_column(cols, "require_otp", "INTEGER DEFAULT 1")
    _ensure_sqlite_column(cols, "mobile_otp_enabled", "INTEGER DEFAULT 1")
    _ensure_sqlite_column(cols, "mobile_otp_hash", "TEXT")
    _ensure_sqlite_column(cols, "mobile_otp_expires_at", "TEXT")
    _ensure_sqlite_column(cols, "mobile_otp_sent_at", "TEXT")
    _ensure_sqlite_column(cols, "totp_enabled", "INTEGER DEFAULT 0")
    _ensure_sqlite_column(cols, "totp_secret", "TEXT")
    _ensure_sqlite_column(cols, "last_otp_verified_at", "TEXT")
    _ensure_sqlite_column(cols, "created_by_admin_id", "INTEGER")
    _ensure_sqlite_column(cols, "password_reset_failed_attempts", "INTEGER DEFAULT 0")
    _ensure_sqlite_column(cols, "password_reset_locked_until", "TEXT")

    properties_exists = query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='properties'"
    )
    if properties_exists:
        p_cols = {str(row.get("name", "")).lower() for row in query_all("PRAGMA table_info(properties)")}
        if "owner_admin_id" not in p_cols:
            execute("ALTER TABLE properties ADD COLUMN owner_admin_id INTEGER")

    submissions_exists = query_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='owner_submissions'"
    )
    if submissions_exists:
        s_cols = {
            str(row.get("name", "")).lower()
            for row in query_all("PRAGMA table_info(owner_submissions)")
        }
        if "owner_admin_id" not in s_cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN owner_admin_id INTEGER")


def _ensure_sqlite_column(existing_cols, col_name, col_type):
    if col_name in existing_cols:
        return
    execute(f"ALTER TABLE admins ADD COLUMN {col_name} {col_type}")


def _ensure_mysql_schema():
    cols = {str(row.get("Field", "")).lower() for row in query_all("SHOW COLUMNS FROM admins")}
    _ensure_mysql_column(cols, "role", "VARCHAR(32) DEFAULT 'executive'")
    _ensure_mysql_column(cols, "permissions_json", "TEXT")
    _ensure_mysql_column(cols, "phone", "VARCHAR(30)")
    _ensure_mysql_column(cols, "phone_verified", "TINYINT(1) DEFAULT 0")
    _ensure_mysql_column(cols, "require_otp", "TINYINT(1) DEFAULT 1")
    _ensure_mysql_column(cols, "mobile_otp_enabled", "TINYINT(1) DEFAULT 1")
    _ensure_mysql_column(cols, "mobile_otp_hash", "VARCHAR(255)")
    _ensure_mysql_column(cols, "mobile_otp_expires_at", "DATETIME NULL")
    _ensure_mysql_column(cols, "mobile_otp_sent_at", "DATETIME NULL")
    _ensure_mysql_column(cols, "totp_enabled", "TINYINT(1) DEFAULT 0")
    _ensure_mysql_column(cols, "totp_secret", "VARCHAR(64)")
    _ensure_mysql_column(cols, "last_otp_verified_at", "DATETIME NULL")
    _ensure_mysql_column(cols, "created_by_admin_id", "INT NULL")
    _ensure_mysql_column(cols, "password_reset_failed_attempts", "INT DEFAULT 0")
    _ensure_mysql_column(cols, "password_reset_locked_until", "DATETIME NULL")

    properties_exists = query_one("SHOW TABLES LIKE 'properties'")
    if properties_exists:
        p_cols = {str(row.get("Field", "")).lower() for row in query_all("SHOW COLUMNS FROM properties")}
        if "owner_admin_id" not in p_cols:
            execute("ALTER TABLE properties ADD COLUMN owner_admin_id INT NULL")

    submissions_exists = query_one("SHOW TABLES LIKE 'owner_submissions'")
    if submissions_exists:
        s_cols = {
            str(row.get("Field", "")).lower()
            for row in query_all("SHOW COLUMNS FROM owner_submissions")
        }
        if "owner_admin_id" not in s_cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN owner_admin_id INT NULL")


def _ensure_mysql_column(existing_cols, col_name, col_type):
    if col_name in existing_cols:
        return
    execute(f"ALTER TABLE admins ADD COLUMN {col_name} {col_type}")


def _normalize_existing_roles_and_permissions():
    execute("UPDATE admins SET role='main_admin' WHERE LOWER(role)='admin'")
    execute("UPDATE admins SET role='main_admin' WHERE LOWER(role)='mainadmin'")
    execute("UPDATE admins SET role='super_admin' WHERE LOWER(role)='superadmin'")
    execute("UPDATE admins SET role='executive' WHERE LOWER(role) IN ('agent','employee')")
    rows = query_all("SELECT id, role, permissions_json FROM admins")
    for row in rows:
        role = _normalize_role(row.get("role"))
        permissions = _parse_permissions(row.get("permissions_json"), role)
        if role in {ROLE_SUPER_ADMIN, ROLE_MAIN_ADMIN}:
            permissions = set(PERMISSION_KEYS)
        elif role == ROLE_EXECUTIVE:
            permissions = {perm for perm in permissions if perm in EXECUTIVE_ALLOWED_PERMISSIONS}
            if not permissions:
                permissions = set(ROLE_PRESETS.get(role, []))
        elif role == ROLE_BROKER:
            permissions = {perm for perm in permissions if perm in BROKER_ALLOWED_PERMISSIONS}
            if not permissions:
                permissions = set(ROLE_PRESETS.get(role, []))
        execute(
            "UPDATE admins SET role=%s, permissions_json=%s WHERE id=%s",
            (role, _serialize_permissions(permissions), row["id"]),
        )


def _resolve_bootstrap_password(explicit_password=None):
    return resolve_bootstrap_admin_password(
        str(explicit_password).strip() if explicit_password else None
    )


class Admin(UserMixin):
    def __init__(self, row):
        _ensure_schema()
        self.id = row["id"]
        self.username = row["username"]
        self.email = row["email"]
        self.password_hash = row["password_hash"]
        self.full_name = row.get("full_name")
        self.role = _normalize_role(row.get("role", ROLE_EXECUTIVE))
        self.permissions = _parse_permissions(row.get("permissions_json"), self.role)
        if self.role in {ROLE_SUPER_ADMIN, ROLE_MAIN_ADMIN}:
            self.permissions = set(PERMISSION_KEYS)
        self.phone = row.get("phone")
        self.phone_verified = bool(row.get("phone_verified", 0))
        self.require_otp = bool(row.get("require_otp", 1))
        self.mobile_otp_enabled = bool(row.get("mobile_otp_enabled", 1))
        self.totp_enabled = bool(row.get("totp_enabled", 0))
        self.totp_secret = row.get("totp_secret")
        self.mobile_otp_hash = row.get("mobile_otp_hash")
        self.mobile_otp_expires_at = _parse_timestamp(row.get("mobile_otp_expires_at"))
        self.mobile_otp_sent_at = _parse_timestamp(row.get("mobile_otp_sent_at"))
        self.last_otp_verified_at = _parse_timestamp(row.get("last_otp_verified_at"))
        self.created_by_admin_id = row.get("created_by_admin_id")
        self.password_reset_failed_attempts = int(row.get("password_reset_failed_attempts") or 0)
        self.password_reset_locked_until = _parse_timestamp(row.get("password_reset_locked_until"))
        self._is_active = bool(row.get("is_active", 1))

    @property
    def is_admin(self):
        return True

    @property
    def is_super_admin(self):
        return self.role in {ROLE_SUPER_ADMIN, ROLE_MAIN_ADMIN}

    @property
    def is_employee(self):
        return not self.is_super_admin

    @property
    def is_active(self):
        return self._is_active

    @property
    def permission_summary(self):
        if self.is_super_admin:
            return "Full access"
        enabled = [p for p in PERMISSION_KEYS if self.has_permission(p)]
        if not enabled:
            return "No permissions"
        if len(enabled) <= 2:
            return ", ".join(enabled)
        return f"{', '.join(enabled[:2])} +{len(enabled) - 2} more"

    @property
    def verification_summary(self):
        parts = []
        parts.append("TOTP On" if self.totp_enabled else "TOTP Off")
        if self.mobile_otp_enabled:
            parts.append("Mobile OTP On")
        else:
            parts.append("Mobile OTP Off")
        parts.append("Phone Verified" if self.phone_verified else "Phone Unverified")
        return " | ".join(parts)

    def has_permission(self, permission_key):
        if self.is_super_admin:
            return True
        if self.role == ROLE_EXECUTIVE and permission_key not in EXECUTIVE_ALLOWED_PERMISSIONS:
            return False
        if self.role == ROLE_BROKER and permission_key not in BROKER_ALLOWED_PERMISSIONS:
            return False
        return permission_key in self.permissions

    def get_id(self):
        return str(self.id)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def matches_phone(self, phone_value):
        expected = _digits_only(self.phone)
        if not expected:
            return True
        provided = _digits_only(phone_value)
        return bool(provided) and provided == expected

    def masked_phone(self):
        digits = _digits_only(self.phone)
        if not digits:
            return ""
        if len(digits) <= 4:
            return f"***{digits}"
        return f"{'*' * max(0, len(digits) - 4)}{digits[-4:]}"

    def _password_reset_lock_remaining_seconds(self):
        if not self.password_reset_locked_until:
            return 0
        remaining = int((self.password_reset_locked_until - _now_utc()).total_seconds())
        return max(0, remaining)

    def can_attempt_password_reset(self):
        fresh = Admin.get_by_id(self.id, include_inactive=True)
        if not fresh:
            return False, "Admin account not found."
        remaining = fresh._password_reset_lock_remaining_seconds()
        if remaining > 0:
            mins = max(1, (remaining + 59) // 60)
            return (
                False,
                f"Too many failed reset attempts. Try again in {mins} minute(s).",
            )
        if fresh.password_reset_locked_until or fresh.password_reset_failed_attempts:
            fresh.clear_password_reset_guard()
        return True, ""

    def clear_password_reset_guard(self):
        execute(
            "UPDATE admins SET password_reset_failed_attempts=0, password_reset_locked_until=NULL WHERE id=%s",
            (self.id,),
        )

    def _record_password_reset_failure(self):
        fresh = Admin.get_by_id(self.id, include_inactive=True)
        if not fresh:
            return {"locked": True, "remaining": _PASSWORD_RESET_COOLDOWN_MINUTES * 60, "attempts_left": 0}
        failed = int(fresh.password_reset_failed_attempts or 0) + 1
        if failed >= _PASSWORD_RESET_MAX_ATTEMPTS:
            lock_until = _now_utc() + timedelta(minutes=_PASSWORD_RESET_COOLDOWN_MINUTES)
            execute(
                "UPDATE admins SET password_reset_failed_attempts=%s, password_reset_locked_until=%s WHERE id=%s",
                (failed, _to_text_timestamp(lock_until), self.id),
            )
            return {
                "locked": True,
                "remaining": _PASSWORD_RESET_COOLDOWN_MINUTES * 60,
                "attempts_left": 0,
            }
        execute(
            "UPDATE admins SET password_reset_failed_attempts=%s WHERE id=%s",
            (failed, self.id),
        )
        return {
            "locked": False,
            "remaining": 0,
            "attempts_left": max(0, _PASSWORD_RESET_MAX_ATTEMPTS - failed),
        }

    def verify_password_reset_otp(self, method, code):
        method = (method or "").strip().lower()
        allowed, reason = self.can_attempt_password_reset()
        if not allowed:
            return False, reason

        if method == "mobile":
            ok, message = self.verify_mobile_otp(code)
        elif method == "totp":
            ok, message = self.verify_totp(code)
        else:
            return False, "Unsupported reset verification method."

        if ok:
            self.clear_password_reset_guard()
            return True, message

        state = self._record_password_reset_failure()
        if state["locked"]:
            return (
                False,
                f"Too many invalid attempts. Password reset is locked for {_PASSWORD_RESET_COOLDOWN_MINUTES} minute(s).",
            )
        attempts_left = state["attempts_left"]
        if attempts_left > 0:
            return False, f"{message} {attempts_left} attempt(s) left."
        return False, message

    @staticmethod
    def validate_new_password(password):
        value = str(password or "")
        if len(value) < 8:
            return False, "Password must be at least 8 characters."
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            return False, "Password must include at least one letter and one number."
        return True, ""

    def update_password(self, new_password):
        valid, message = Admin.validate_new_password(new_password)
        if not valid:
            return False, message
        execute(
            """UPDATE admins
               SET password_hash=%s,
                   mobile_otp_hash=NULL,
                   mobile_otp_expires_at=NULL,
                   password_reset_failed_attempts=0,
                   password_reset_locked_until=NULL
               WHERE id=%s""",
            (generate_password_hash(new_password), self.id),
        )
        return True, "Password updated successfully."

    def requires_login_otp(self):
        return bool(self.require_otp or self.totp_enabled or self.mobile_otp_enabled)

    def can_use_totp(self):
        return bool(self.totp_enabled and self.totp_secret)

    def can_use_mobile_otp(self):
        return bool(self.mobile_otp_enabled and self.phone)

    def issue_mobile_otp(self, force=False):
        if not self.can_use_mobile_otp():
            return {
                "ok": False,
                "fallback": False,
                "message": "Mobile OTP is not configured for this account.",
                "dev_code": None,
            }
        now = _now_utc()
        if not force and self.mobile_otp_sent_at and (now - self.mobile_otp_sent_at).seconds < 30:
            return {
                "ok": True,
                "message": "OTP already sent recently. Please wait a few seconds before retrying.",
                "fallback": False,
                "dev_code": None,
            }

        code = f"{secrets.randbelow(10**6):06d}"
        expiry_at = now + timedelta(minutes=_OTP_EXPIRY_MINUTES)
        result = send_mobile_otp_code(self.phone, code, self.username)
        if not result.get("ok"):
            return result

        execute(
            """UPDATE admins
               SET mobile_otp_hash=%s, mobile_otp_expires_at=%s, mobile_otp_sent_at=%s
               WHERE id=%s""",
            (
                generate_password_hash(code),
                _to_text_timestamp(expiry_at),
                _to_text_timestamp(now),
                self.id,
            ),
        )
        self.mobile_otp_hash = "set"
        self.mobile_otp_expires_at = expiry_at
        self.mobile_otp_sent_at = now
        return result

    def verify_mobile_otp(self, code):
        code = (code or "").strip()
        if not code or len(code) < 4:
            return False, "Enter a valid OTP code."
        fresh = Admin.get_by_id(self.id, include_inactive=True)
        if not fresh or not fresh.mobile_otp_hash:
            return False, "OTP not requested. Please request a new OTP."
        if not fresh.mobile_otp_expires_at or fresh.mobile_otp_expires_at < _now_utc():
            return False, "OTP expired. Request a new code."
        if not check_password_hash(fresh.mobile_otp_hash, code):
            return False, "Invalid mobile OTP."

        execute(
            """UPDATE admins
               SET mobile_otp_hash=NULL,
                   mobile_otp_expires_at=NULL,
                   last_otp_verified_at=%s,
                   phone_verified=%s
               WHERE id=%s""",
            (_to_text_timestamp(_now_utc()), 1 if self.phone else 0, self.id),
        )
        return True, "Mobile OTP verified."

    def verify_totp(self, code):
        code = (code or "").strip().replace(" ", "")
        if not self.can_use_totp():
            return False, "TOTP is not enabled for this account."
        if not code:
            return False, "Enter the authenticator code."
        totp = pyotp.TOTP(self.totp_secret)
        if not totp.verify(code, valid_window=1):
            return False, "Invalid authenticator code."
        execute(
            "UPDATE admins SET last_otp_verified_at=%s WHERE id=%s",
            (_to_text_timestamp(_now_utc()), self.id),
        )
        return True, "Authenticator code verified."

    @staticmethod
    def _sanitize_permissions(role, selected_permissions):
        cleaned = {p for p in (selected_permissions or []) if p in PERMISSION_KEYS}
        if role in {ROLE_SUPER_ADMIN, ROLE_MAIN_ADMIN}:
            return set(PERMISSION_KEYS)
        if role == ROLE_EXECUTIVE:
            cleaned = {perm for perm in cleaned if perm in EXECUTIVE_ALLOWED_PERMISSIONS}
            return cleaned or set(ROLE_PRESETS.get(role, []))
        if role == ROLE_BROKER:
            cleaned = {perm for perm in cleaned if perm in BROKER_ALLOWED_PERMISSIONS}
            return cleaned or set(ROLE_PRESETS.get(role, []))
        return cleaned or set(ROLE_PRESETS.get(role, []))

    @staticmethod
    def list_admins(include_inactive=True):
        _ensure_schema()
        sql = "SELECT * FROM admins"
        if not include_inactive:
            sql += " WHERE is_active=1"
        sql += " ORDER BY CASE WHEN role IN ('super_admin','main_admin') THEN 0 ELSE 1 END, created_at DESC"
        rows = query_all(sql)
        return [Admin(row) for row in rows]

    @staticmethod
    def get_by_id(admin_id, include_inactive=False):
        _ensure_schema()
        sql = "SELECT * FROM admins WHERE id=%s"
        params = [admin_id]
        if not include_inactive:
            sql += " AND is_active=1"
        row = query_one(sql, params)
        return Admin(row) if row else None

    @staticmethod
    def get_by_username(username, include_inactive=False):
        _ensure_schema()
        sql = "SELECT * FROM admins WHERE username=%s"
        params = [username]
        if not include_inactive:
            sql += " AND is_active=1"
        row = query_one(sql, params)
        return Admin(row) if row else None

    @staticmethod
    def get_by_email(email, include_inactive=False):
        _ensure_schema()
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        sql = "SELECT * FROM admins WHERE LOWER(email)=LOWER(%s)"
        params = [normalized]
        if not include_inactive:
            sql += " AND is_active=1"
        row = query_one(sql, params)
        return Admin(row) if row else None

    @staticmethod
    def get_default_owner_admin_id():
        _ensure_schema()
        preferred = query_one(
            "SELECT id FROM admins WHERE role IN ('super_admin','main_admin') AND is_active=1 ORDER BY id ASC LIMIT 1"
        )
        if preferred:
            return preferred["id"]
        fallback = query_one("SELECT id FROM admins WHERE is_active=1 ORDER BY id ASC LIMIT 1")
        return fallback["id"] if fallback else None

    @staticmethod
    def create_admin(data, created_by_admin_id=None):
        _ensure_schema()
        role = _normalize_role(data.get("role"))
        permissions = Admin._sanitize_permissions(role, data.get("permissions"))
        require_otp = bool(data.get("require_otp", True))
        mobile_otp_enabled = bool(data.get("mobile_otp_enabled", True))
        phone_value = (data.get("phone") or "").strip()[:30] or None
        if mobile_otp_enabled and not phone_value:
            raise ValueError("Phone number is required when mobile OTP is enabled.")
        if require_otp and not mobile_otp_enabled:
            raise ValueError("Require OTP needs at least one OTP method enabled.")

        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        if not username:
            raise ValueError("Username is required.")
        if not email:
            email = f"{username}@jakkash.local"
        if Admin.get_by_username(username, include_inactive=True):
            raise ValueError("Username already exists.")
        existing_email = query_one("SELECT id FROM admins WHERE LOWER(email)=LOWER(%s)", (email,))
        if existing_email:
            raise ValueError("Email already exists.")

        password = data.get("password") or ""
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        admin_id = execute(
            """INSERT INTO admins
               (username, email, password_hash, full_name, role, permissions_json,
                is_active, phone, phone_verified, require_otp, mobile_otp_enabled,
                totp_enabled, totp_secret, created_by_admin_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                username,
                email,
                generate_password_hash(password),
                (data.get("full_name") or username).strip()[:120],
                role,
                _serialize_permissions(permissions),
                1 if data.get("is_active", True) else 0,
                phone_value,
                1 if data.get("phone_verified") else 0,
                1 if require_otp else 0,
                1 if mobile_otp_enabled else 0,
                0,
                None,
                created_by_admin_id,
            ),
        )
        return Admin.get_by_id(admin_id, include_inactive=True)

    @staticmethod
    def update_admin(admin_id, data):
        _ensure_schema()
        current = Admin.get_by_id(admin_id, include_inactive=True)
        if not current:
            raise ValueError("Admin not found.")

        role = _normalize_role(data.get("role", current.role))
        permissions = Admin._sanitize_permissions(role, data.get("permissions"))
        is_active = bool(data.get("is_active", current.is_active))
        demoting_full_access = role not in {ROLE_SUPER_ADMIN, ROLE_MAIN_ADMIN}
        if current.is_super_admin and (not is_active or demoting_full_access):
            if _active_full_admin_count(exclude_admin_id=admin_id) <= 0:
                raise ValueError("At least one active full-control admin is required.")

        phone_value = (data.get("phone") or "").strip()[:30] or None
        require_otp = bool(data.get("require_otp", current.require_otp))
        mobile_otp_enabled = bool(data.get("mobile_otp_enabled", current.mobile_otp_enabled))
        if mobile_otp_enabled and not phone_value:
            raise ValueError("Phone number is required when mobile OTP is enabled.")
        if require_otp and not (mobile_otp_enabled or current.totp_enabled):
            raise ValueError("Require OTP needs mobile OTP or TOTP enabled.")

        password = (data.get("password") or "").strip()
        password_hash = current.password_hash if not password else generate_password_hash(password)
        if password and len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        next_email = (data.get("email") or current.email).strip().lower()
        existing_email = query_one(
            "SELECT id FROM admins WHERE LOWER(email)=LOWER(%s) AND id!=%s",
            (next_email, admin_id),
        )
        if existing_email:
            raise ValueError("Email already exists.")

        execute(
            """UPDATE admins
               SET full_name=%s,
                   email=%s,
                   role=%s,
                   permissions_json=%s,
                   is_active=%s,
                   phone=%s,
                   phone_verified=%s,
                   require_otp=%s,
                   mobile_otp_enabled=%s,
                   password_hash=%s
               WHERE id=%s""",
            (
                (data.get("full_name") or current.full_name or current.username).strip()[:120],
                next_email,
                role,
                _serialize_permissions(permissions),
                1 if is_active else 0,
                phone_value,
                1 if data.get("phone_verified") else 0,
                1 if require_otp else 0,
                1 if mobile_otp_enabled else 0,
                password_hash,
                admin_id,
            ),
        )
        return Admin.get_by_id(admin_id, include_inactive=True)

    @staticmethod
    def toggle_active(admin_id, is_active):
        _ensure_schema()
        target = Admin.get_by_id(admin_id, include_inactive=True)
        if not target:
            raise ValueError("Admin not found.")
        if target.is_super_admin and not is_active and _active_full_admin_count(exclude_admin_id=admin_id) <= 0:
            raise ValueError("At least one active full-control admin is required.")
        execute("UPDATE admins SET is_active=%s WHERE id=%s", (1 if is_active else 0, admin_id))

    @staticmethod
    def delete_admin(admin_id):
        _ensure_schema()
        target = Admin.get_by_id(admin_id, include_inactive=True)
        if not target:
            return
        if target.is_super_admin and _active_full_admin_count(exclude_admin_id=admin_id) <= 0:
            raise ValueError("Cannot delete the last full-control admin.")
        execute("UPDATE admins SET is_active=0 WHERE id=%s", (admin_id,))

    @staticmethod
    def ensure_totp_secret(admin_id, regenerate=False):
        _ensure_schema()
        target = Admin.get_by_id(admin_id, include_inactive=True)
        if not target:
            raise ValueError("Admin not found.")
        secret = target.totp_secret
        if regenerate or not secret:
            secret = pyotp.random_base32()
        execute(
            "UPDATE admins SET totp_secret=%s, totp_enabled=1, require_otp=1 WHERE id=%s",
            (secret, admin_id),
        )
        refreshed = Admin.get_by_id(admin_id, include_inactive=True)
        return secret, refreshed

    @staticmethod
    def disable_totp(admin_id):
        _ensure_schema()
        execute("UPDATE admins SET totp_enabled=0, totp_secret=NULL WHERE id=%s", (admin_id,))

    @staticmethod
    def totp_setup_payload(admin_obj):
        if not admin_obj:
            return None
        secret = admin_obj.totp_secret
        if not secret:
            return None
        issuer = COMPANY_NAME.replace(" ", "")
        account_name = f"{admin_obj.username}@admin"
        uri = pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)
        from urllib.parse import quote_plus

        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={quote_plus(uri)}"
        return {
            "admin_id": admin_obj.id,
            "username": admin_obj.username,
            "secret": secret,
            "otpauth_uri": uri,
            "qr_url": qr_url,
        }

    @staticmethod
    def ensure_default(password=None):
        _ensure_schema()
        existing_admin = query_one(
            "SELECT id, username, email, full_name FROM admins WHERE LOWER(username)=LOWER(%s)",
            (DEFAULT_BOOTSTRAP_ADMIN_USERNAME,),
        )
        legacy_admin = query_one(
            "SELECT id, username, email, full_name FROM admins WHERE LOWER(username)=LOWER(%s)",
            (LEGACY_BOOTSTRAP_ADMIN_USERNAME,),
        )

        if not existing_admin and legacy_admin:
            execute(
                """UPDATE admins
                   SET username=%s,
                       full_name=%s,
                       password_hash=%s
                   WHERE id=%s""",
                (
                    DEFAULT_BOOTSTRAP_ADMIN_USERNAME,
                    DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME,
                    bootstrap_password_hash(password),
                    legacy_admin["id"],
                ),
            )
            existing_admin = query_one(
                "SELECT id, username, email, full_name FROM admins WHERE id=%s",
                (legacy_admin["id"],),
            )
            legacy_admin = None

        if existing_admin and legacy_admin and legacy_admin["id"] != existing_admin["id"]:
            execute("UPDATE admins SET is_active=0 WHERE id=%s", (legacy_admin["id"],))

        if existing_admin:
            existing_email = (existing_admin.get("email") or "").lower()
            if not existing_email or existing_email.endswith("@jakkashproperty.com"):
                execute(
                    "UPDATE admins SET email=%s WHERE id=%s",
                    (DEFAULT_BOOTSTRAP_ADMIN_EMAIL, existing_admin["id"]),
                )
            execute(
                """UPDATE admins
                   SET role='super_admin',
                       permissions_json=%s,
                       require_otp=1,
                       mobile_otp_enabled=1,
                       phone=COALESCE(phone,%s),
                       full_name=CASE
                           WHEN full_name IS NULL OR TRIM(full_name)=''
                           THEN %s
                           ELSE full_name
                       END
                   WHERE id=%s""",
                (
                    _serialize_permissions(PERMISSION_KEYS),
                    COMPANY_PHONE_RAW,
                    DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME,
                    existing_admin["id"],
                ),
            )
            # Sync password from env when explicitly configured (never hardcode admin123 on Vercel).
            if os.getenv("VERCEL") and use_sqlite():
                env_pw = _read_admin_initial_password()
                if env_pw:
                    execute(
                        "UPDATE admins SET password_hash=%s, is_active=1 WHERE id=%s",
                        (bootstrap_password_hash(env_pw), existing_admin["id"]),
                    )
            return

        pw = bootstrap_password_hash(password)
        execute(
            """INSERT INTO admins
               (username, email, password_hash, full_name, role, permissions_json, require_otp, mobile_otp_enabled, phone)
               VALUES (%s,%s,%s,%s,'super_admin',%s,1,1,%s)""",
            (
                DEFAULT_BOOTSTRAP_ADMIN_USERNAME,
                DEFAULT_BOOTSTRAP_ADMIN_EMAIL,
                pw,
                DEFAULT_BOOTSTRAP_ADMIN_FULL_NAME,
                _serialize_permissions(PERMISSION_KEYS),
                COMPANY_PHONE_RAW,
            ),
        )
