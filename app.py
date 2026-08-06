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

    @app.route("/uploads/<path:filename>")
    def uploads(filename):
        upload_roots = [
            os.path.join(app.root_path, "uploads"),
            os.path.join(app.root_path, "public", "uploads"),
            os.path.join(app.root_path, "static", "property-uploads"),
        ]
        for root in upload_roots:
            directory = os.path.abspath(root)
            full_path = os.path.abspath(os.path.join(directory, filename))
            if full_path.startswith(directory) and os.path.isfile(full_path):
                return send_from_directory(directory, filename)
        return "File not found", 404

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
