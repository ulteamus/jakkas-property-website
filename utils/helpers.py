import re
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from flask import current_app


def slugify(text):
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s[:200] or str(uuid.uuid4())[:8]


def format_inr(amount):
    try:
        return f"₹{float(amount):,.0f}"
    except (TypeError, ValueError):
        return "₹0"


def property_upload_dir(property_id, media_type="images"):
    root = Path(current_app.config["UPLOAD_ROOT"]) / str(property_id) / media_type
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_upload(file, property_id, media_type, allowed):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        return None
    folder = property_upload_dir(property_id, media_type)
    name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = folder / name
    file.save(path)
    return f"properties/{property_id}/{media_type}/{name}"


def whatsapp_url(message):
    from config import COMPANY_WHATSAPP
    import urllib.parse
    return f"https://wa.me/{COMPANY_WHATSAPP}?text={urllib.parse.quote(message)}"
