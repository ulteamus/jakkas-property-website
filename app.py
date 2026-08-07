import os
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, session
from flask_wtf.csrf import CSRFError
from jinja2 import ChoiceLoader
import uuid

from config import (
    Config,
    UPLOAD_ROOT,
    COMPANY_NAME,
    COMPANY_OWNER,
    COMPANY_ADDRESS,
    COMPANY_PHONE,
    COMPANY_EMAIL,
    COMPANY_WHATSAPP,
    COMPANY_LAT,
    COMPANY_LNG,
)
from extensions import login_manager, csrf
from database import close_connection, test_connection
from models.admin import Admin


def create_app():
    root = Path(__file__).resolve().parent
    api_root = root / "api"
    if (api_root / "templates").exists():
        template_folder = str(api_root / "templates")
        static_folder = str(api_root / "static")
    else:
        template_folder = str(root / "templates")
        static_folder = str(root / "static")

    app = Flask(
        __name__,
        template_folder=template_folder,
        static_folder=static_folder,
        static_url_path="/static",
    )

    try:
        from api.template_store import loader as template_loader

        app.jinja_loader = ChoiceLoader([template_loader(), app.jinja_loader])
    except Exception:
        pass
    app.config.from_object(Config)
    app.config["UPLOAD_ROOT"] = str(UPLOAD_ROOT)

    for folder in (UPLOAD_ROOT, Path("ml/models"), Path("static/img")):
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    login_manager.init_app(app)
    csrf.init_app(app)
    app.teardown_appcontext(close_connection)

    @login_manager.user_loader
    def load_user(user_id):
        return Admin.get_by_id(int(user_id))

    from routes.public import public_bp
    from routes.auth import auth_bp
    from routes.api import api_bp
    from routes.admin_portal import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_company():
        return {
            "company_name": COMPANY_NAME,
            "company_owner": COMPANY_OWNER,
            "company_address": COMPANY_ADDRESS,
            "company_phone": COMPANY_PHONE,
            "company_phone_raw": re.sub(r"\D", "", COMPANY_PHONE),
            "company_email": COMPANY_EMAIL,
            "company_whatsapp": COMPANY_WHATSAPP,
            "company_lat": COMPANY_LAT,
            "company_lng": COMPANY_LNG,
        }

    @app.before_request
    def ensure_session_ids():
        session.permanent = True
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        if "visitor_id" not in session:
            session["visitor_id"] = str(uuid.uuid4())

    def _normalize_upload_relpath(filename):
        name = (filename or "").replace("\\", "/").lstrip("/")
        for prefix in (
            "uploads/",
            "static/property-uploads/",
            "property-uploads/",
            "api/static/property-uploads/",
        ):
            if name.startswith(prefix):
                name = name[len(prefix) :]
        # Repair accidental double "properties/properties/" from older url_for rules.
        while name.startswith("properties/properties/"):
            name = name[len("properties/") :]
        return name

    def _upload_candidate_roots():
        upload_root = Path(app.config.get("UPLOAD_ROOT") or UPLOAD_ROOT)
        return [
            upload_root.parent,  # .../uploads  (paths like properties/ID/images/x.jpg)
            upload_root,  # .../uploads/properties (paths like ID/images/x.jpg)
            Path(app.root_path) / "uploads",
            Path(app.root_path) / "public" / "uploads",
            Path(app.root_path) / "static" / "property-uploads",
            Path(app.root_path) / "api" / "static" / "property-uploads",
            Path(app.static_folder or "") / "property-uploads",
        ]

    def _serve_default_property_image():
        """Serve a clean placeholder when an upload path is missing (no broken 404)."""
        candidates = [
            Path(app.root_path) / "static" / "img" / "default-property.jpg",
            Path(app.root_path) / "static" / "img" / "placeholder.jpg",
            Path(app.root_path) / "api" / "static" / "img" / "default-property.jpg",
            Path(app.root_path) / "api" / "static" / "img" / "placeholder.jpg",
            Path(app.static_folder or "") / "img" / "default-property.jpg",
            Path(app.static_folder or "") / "img" / "placeholder.jpg",
        ]
        for path in candidates:
            try:
                if path.is_file():
                    resp = send_from_directory(str(path.parent), path.name)
                    resp.headers["Cache-Control"] = "public, max-age=86400"
                    return resp
            except OSError:
                continue
        # Absolute last resort: 1x1 JPEG bytes so clients never get an empty 404 body.
        import io
        from flask import send_file
        try:
            from PIL import Image as _Image
            buf = io.BytesIO()
            _Image.new("RGB", (1200, 800), (40, 40, 40)).save(buf, format="JPEG", quality=70)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg")
        except Exception:
            return "placeholder unavailable", 404

    @app.route("/static/img/default-property.jpg")
    @app.route("/static/img/placeholder.jpg")
    def default_property_image():
        return _serve_default_property_image()

    def _serve_upload_file(filename):
        rel = _normalize_upload_relpath(filename)
        if not rel or ".." in rel.split("/"):
            return _serve_default_property_image()

        # Also try without a leading "properties/" when searching UPLOAD_ROOT.
        alt_rel = rel[len("properties/") :] if rel.startswith("properties/") else None

        for root in _upload_candidate_roots():
            try:
                directory = root.resolve()
            except OSError:
                continue
            if not directory.is_dir():
                continue
            for candidate in (rel, alt_rel):
                if not candidate:
                    continue
                full_path = (directory / candidate).resolve()
                try:
                    full_path.relative_to(directory)
                except ValueError:
                    continue
                if full_path.is_file():
                    return send_from_directory(str(directory), candidate)
        return _serve_default_property_image()

    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        # Single route so url_for('uploads', filename='properties/...') stays
        # /uploads/properties/... (not /uploads/properties/properties/...).
        return _serve_upload_file(filename)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(exc):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "CSRF token missing or invalid."}), 400
        return exc.description, 400

    with app.app_context():
        try:
            if test_connection():
                Admin.ensure_default()
        except Exception:
            pass

    return app


app = create_app()

if __name__ == "__main__":
    application = app
    debug_enabled = os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    try:
        port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    except (TypeError, ValueError):
        port = 5000
    application.run(debug=debug_enabled, host=host, port=port)
