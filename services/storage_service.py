"""Persistent media storage — Cloudinary when configured, local disk otherwise."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def cloudinary_configured() -> bool:
    if (os.getenv("CLOUDINARY_URL") or "").strip():
        return True
    return all(
        (os.getenv(key) or "").strip()
        for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    )


def _configure_cloudinary() -> None:
    import cloudinary

    url = (os.getenv("CLOUDINARY_URL") or "").strip()
    if url:
        cloudinary.config(cloudinary_url=url, secure=True)
        return
    cloudinary.config(
        cloud_name=(os.getenv("CLOUDINARY_CLOUD_NAME") or "").strip(),
        api_key=(os.getenv("CLOUDINARY_API_KEY") or "").strip(),
        api_secret=(os.getenv("CLOUDINARY_API_SECRET") or "").strip(),
        secure=True,
    )


def _resource_type(media_type: str, ext: str) -> str:
    if media_type == "videos" or ext in {"mp4", "mov", "webm"}:
        return "video"
    if media_type == "documents" or ext == "pdf":
        return "raw"
    return "image"


def _local_save(file_storage: FileStorage, property_id, media_type: str, ext: str) -> str:
    root = Path(current_app.config["UPLOAD_ROOT"]) / str(property_id) / media_type
    root.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = root / name
    file_storage.save(path)
    return f"properties/{property_id}/{media_type}/{name}"


def _cloudinary_save(file_storage: FileStorage, property_id, media_type: str, ext: str) -> str:
    from cloudinary.uploader import upload as cloudinary_upload

    _configure_cloudinary()
    public_id = f"{uuid.uuid4().hex[:16]}"
    folder = f"jakkash/properties/{property_id}/{media_type}"
    resource_type = _resource_type(media_type, ext)
    # Rewind stream if previously read.
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass
    result = cloudinary_upload(
        file_storage,
        folder=folder,
        public_id=public_id,
        resource_type=resource_type,
        overwrite=False,
        use_filename=False,
        unique_filename=True,
    )
    url = (result.get("secure_url") or result.get("url") or "").strip()
    if not url:
        raise RuntimeError("Cloudinary upload returned no URL.")
    return url


def save_media(file_storage, property_id, media_type, allowed) -> str | None:
    """
    Persist an uploaded file.

    Returns a permanent HTTPS Cloudinary URL when credentials are set,
    otherwise a relative local path like properties/<id>/<type>/<file>.
    """
    if not file_storage or not getattr(file_storage, "filename", None):
        return None
    filename = secure_filename(file_storage.filename) or file_storage.filename
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        return None

    if cloudinary_configured():
        try:
            return _cloudinary_save(file_storage, property_id, media_type, ext)
        except Exception as exc:
            # Fall back to local so a misconfigured Cloudinary key does not
            # drop the upload entirely in non-Vercel environments.
            current_app.logger.warning("Cloudinary upload failed (%s); using local storage.", exc)

    return _local_save(file_storage, property_id, media_type, ext)


def is_remote_url(path: str | None) -> bool:
    value = (path or "").strip().lower()
    return value.startswith("http://") or value.startswith("https://")
