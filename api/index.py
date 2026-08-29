"""
Vercel serverless entry — WSGI handler for the Flask app.

Exposes `app` for @vercel/python. Sets VERCEL=1 so create_app() picks embedded
api/templates and api/static via template_store.
"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("VERCEL", "1")

from flask import jsonify, make_response, request

from app import create_app
from database.db import DatabaseUnavailableError, last_db_error

app = create_app()

_CORS_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
_CORS_HEADERS = "Content-Type, Authorization, X-CSRFToken, X-Requested-With"

_DEBUG = os.getenv("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"} or (
    os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
)


def _wants_json() -> bool:
    if request.path.startswith("/api/"):
        return True
    accept = (request.headers.get("Accept") or "").lower()
    return "application/json" in accept and "text/html" not in accept


def _diagnostic_html(title: str, message: str, detail: str = "") -> str:
    safe_detail = (detail or "").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;background:#0f172a;color:#e2e8f0}}
.banner{{background:#7f1d1d;border:1px solid #f87171;padding:1rem 1.25rem;border-radius:8px;max-width:720px}}
code,pre{{background:#1e293b;padding:.5rem;border-radius:6px;display:block;overflow:auto;white-space:pre-wrap}}
a{{color:#93c5fd}}
</style></head><body>
<div class="banner">
  <h1 style="margin-top:0">{title}</h1>
  <p>{message}</p>
  {"<pre>" + safe_detail + "</pre>" if safe_detail and _DEBUG else ""}
  <p><a href="/admin/login">Admin login</a> · <a href="/">Home</a></p>
</div>
</body></html>"""


@app.before_request
def _vercel_preflight():
    if request.method != "OPTIONS":
        return None
    if not os.getenv("VERCEL") and not request.path.startswith("/api/"):
        return None
    resp = make_response("", 204)
    resp.headers["Access-Control-Allow-Methods"] = _CORS_METHODS
    resp.headers["Access-Control-Allow-Headers"] = _CORS_HEADERS
    resp.headers["Access-Control-Max-Age"] = "86400"
    origin = request.headers.get("Origin")
    if origin:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Credentials"] = "true"
    else:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


@app.after_request
def _vercel_cors(response):
    """CORS for JSON API consumers; SSR pages unchanged."""
    if not (os.getenv("VERCEL") or request.path.startswith("/api/")):
        return response
    origin = request.headers.get("Origin")
    if origin:
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Access-Control-Allow-Credentials", "true")
    elif request.path.startswith("/api/"):
        response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", _CORS_METHODS)
    response.headers.setdefault("Access-Control-Allow-Headers", _CORS_HEADERS)
    # Soft diagnostic header when DB degraded
    err = last_db_error()
    if err:
        response.headers.setdefault("X-Jakkas-DB-Warning", err[:200])
    return response


@app.errorhandler(DatabaseUnavailableError)
def _db_unavailable(exc):
    payload = {
        "success": False,
        "error": "database_unavailable",
        "message": str(exc) or "Database is temporarily unavailable.",
    }
    if _DEBUG:
        payload["traceback"] = traceback.format_exc()
    if _wants_json():
        return jsonify(payload), 503
    html = _diagnostic_html(
        "Database unavailable",
        "The app could not reach PostgreSQL. Check SUPABASE_DB_URL on Vercel "
        "(must be a cloud host, not 127.0.0.1). Login page still loads when possible.",
        traceback.format_exc() if _DEBUG else str(exc),
    )
    return make_response(html, 503)


@app.errorhandler(404)
def _not_found(exc):
    if _wants_json():
        return jsonify({"success": False, "error": "Not found."}), 404
    return exc


@app.errorhandler(500)
def _server_error(exc):
    tb = traceback.format_exc()
    app.logger.error("Unhandled error: %s\n%s", exc, tb)
    if _wants_json():
        body = {"success": False, "error": "Internal server error."}
        if _DEBUG:
            body["detail"] = str(exc)
            body["traceback"] = tb
        return jsonify(body), 500
    if _DEBUG:
        html = _diagnostic_html("Server error", str(exc), tb)
        return make_response(html, 500)
    return exc


@app.errorhandler(Exception)
def _unhandled(exc):
    """Global catch for WSGI cold-start / unexpected failures."""
    if isinstance(exc, DatabaseUnavailableError):
        return _db_unavailable(exc)
    # Let HTTPException pass through Flask's default handling
    from werkzeug.exceptions import HTTPException

    if isinstance(exc, HTTPException):
        return exc
    tb = traceback.format_exc()
    app.logger.error("Unhandled exception: %s\n%s", exc, tb)
    if _wants_json():
        body = {"success": False, "error": "Internal server error."}
        if _DEBUG:
            body["detail"] = str(exc)
            body["traceback"] = tb
        return jsonify(body), 500
    html = _diagnostic_html(
        "Unexpected error",
        "The server hit an unexpected error. Enable FLASK_DEBUG=1 for details.",
        tb if _DEBUG else str(exc),
    )
    return make_response(html, 500)
