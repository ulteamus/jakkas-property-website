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

app = create_app()

_CORS_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
_CORS_HEADERS = "Content-Type, Authorization, X-CSRFToken, X-Requested-With"


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
    return response


@app.errorhandler(404)
def _not_found(exc):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Not found."}), 404
    return exc


@app.errorhandler(500)
def _server_error(exc):
    if request.path.startswith("/api/"):
        if os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}:
            return jsonify({"success": False, "error": str(exc)}), 500
        return jsonify({"success": False, "error": "Internal server error."}), 500
    app.logger.error("Unhandled error: %s\n%s", exc, traceback.format_exc())
    return exc
