"""Verify P0/P1 security patches — bootstrap, secret key, media upload auth."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _reset_env(**overrides):
    for key in (
        "VERCEL",
        "ENV",
        "FLASK_ENV",
        "FLASK_DEBUG",
        "DEBUG",
        "SECRET_KEY",
        "FLASK_SECRET_KEY",
        "ADMIN_INITIAL_PASSWORD",
        "DEFAULT_ADMIN_PASSWORD",
        "USE_SQLITE",
    ):
        os.environ.pop(key, None)
    os.environ.update(overrides)


def test_production_secret_required():
    import subprocess
    import tempfile

    snippet = ROOT / "config.py"
    code = f"""
import os
import sys
import importlib.util
os.environ.pop("SECRET_KEY", None)
os.environ.pop("FLASK_SECRET_KEY", None)
os.environ["VERCEL"] = "1"
spec = importlib.util.spec_from_file_location("cfg", r"{snippet}")
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    mod.resolve_secret_key()
except RuntimeError as exc:
    if "SECRET_KEY" in str(exc):
        sys.exit(0)
    raise
sys.exit(2)
"""
    with tempfile.TemporaryDirectory() as tmp:
        env = {"VERCEL": "1", "PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=tmp,
            env=env,
            capture_output=True,
            text=True,
        )
    if result.returncode == 0:
        print("PASS: production startup rejects missing secret key")
        return True
    print("FAIL: production secret check exit", result.returncode, result.stderr or result.stdout)
    return False


def test_unauthenticated_media_upload():
    _reset_env(
        USE_SQLITE="1",
        FLASK_SECRET_KEY="verify-test-secret",
        FLASK_ENV="development",
    )
    import importlib

    import config

    importlib.reload(config)
    from app import create_app

    app = create_app()
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    client = app.test_client()
    resp = client.post(
        "/api/media/upload",
        data={"property_id": "1", "media_type": "images"},
    )
    if resp.status_code not in (401, 403):
        print("FAIL: unauthenticated upload returned", resp.status_code, resp.get_json())
        return False
    print("PASS: unauthenticated media upload returns", resp.status_code)
    return True


def test_local_dev_login():
    _reset_env(
        USE_SQLITE="1",
        FLASK_SECRET_KEY="verify-test-secret",
        FLASK_ENV="development",
    )
    import importlib

    import config

    importlib.reload(config)
    from app import create_app
    from database.db import query_one
    from werkzeug.security import check_password_hash

    app = create_app()
    with app.app_context():
        from models.admin import Admin

        Admin.ensure_default()
        admin = query_one("SELECT * FROM admins WHERE username = %s", ("sam",))
        if not admin:
            print("FAIL: sam admin missing")
            return False
        if not check_password_hash(admin["password_hash"], "admin123"):
            print("FAIL: local dev bootstrap password is not admin123")
            return False
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["TESTING"] = True
    client = app.test_client()
    resp = client.post(
        "/admin/login",
        data={"username": "sam", "password": "admin123"},
        follow_redirects=False,
    )
    if resp.status_code not in (302, 303):
        print("FAIL: local login returned", resp.status_code)
        return False
    print("PASS: local development login works (sam/admin123)")
    return True


def main() -> int:
    results = [
        test_production_secret_required(),
        test_unauthenticated_media_upload(),
        test_local_dev_login(),
    ]
    if all(results):
        print("ALL SECURITY VERIFICATION TESTS PASSED")
        return 0
    print("SECURITY VERIFICATION FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
