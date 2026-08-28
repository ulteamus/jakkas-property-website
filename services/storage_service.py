"""Persistent media storage — Supabase first, then Cloudinary, else local disk."""
from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

DEFAULT_SUPABASE_BUCKET = "property-media"


def _env(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def storage_backend_preference() -> str:
    """local | supabase | cloudinary | auto (empty)."""
    return (_env("STORAGE_BACKEND") or "auto").lower()


def supabase_configured() -> bool:
    return bool(_env("SUPABASE_URL") and _env(
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_ANON_KEY",
    ))


def cloudinary_configured() -> bool:
    if _env("CLOUDINARY_URL"):
        return True
    return all(
        _env(key)
        for key in ("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET")
    )


def supabase_bucket_name() -> str:
    return _env("SUPABASE_BUCKET", "SUPABASE_STORAGE_BUCKET") or DEFAULT_SUPABASE_BUCKET


def _use_supabase_storage() -> bool:
    pref = storage_backend_preference()
    if pref in {"local", "cloudinary"}:
        return False
    if pref in {"supabase", "auto", ""}:
        return supabase_configured()
    return supabase_configured()


def _use_cloudinary_storage() -> bool:
    pref = storage_backend_preference()
    if pref == "local":
        return False
    if pref == "cloudinary":
        return cloudinary_configured()
    if pref == "supabase":
        return False
    return cloudinary_configured()


def _supabase_client():
    from supabase import create_client

    url = _env("SUPABASE_URL").rstrip("/")
    key = _env(
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_ANON_KEY",
    )
    if not url or not key:
        raise RuntimeError("Supabase credentials are not configured.")
    return create_client(url, key)


def _ensure_supabase_bucket(client, bucket: str) -> None:
    """Create a public bucket when missing; ignore if it already exists."""
    try:
        existing = {item.get("name") for item in (client.storage.list_buckets() or [])}
        if bucket in existing:
            return
    except Exception:
        # list_buckets may fail with anon key — still try create / upload.
        existing = set()

    try:
        client.storage.create_bucket(
            bucket,
            options={
                "public": True,
                "file_size_limit": 50 * 1024 * 1024,
                "allowed_mime_types": None,
            },
        )
    except Exception as exc:
        # Bucket may already exist or policy may block create — upload can still work.
        try:
            current_app.logger.info("Supabase bucket ensure note: %s", exc)
        except Exception:
            pass


def _content_type(filename: str, media_type: str, ext: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    if media_type == "videos" or ext in {"mp4", "mov", "webm"}:
        return f"video/{'quicktime' if ext == 'mov' else ext}"
    if media_type == "documents" or ext == "pdf":
        return "application/pdf"
    if ext == "jpg":
        return "image/jpeg"
    return f"image/{ext}"


def _read_bytes(file_storage: FileStorage) -> bytes:
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass
    data = file_storage.read()
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass
    return data


def _local_save(file_storage: FileStorage, property_id, media_type: str, ext: str) -> str:
    root = Path(current_app.config["UPLOAD_ROOT"]) / str(property_id) / media_type
    root.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}.{ext}"
    path = root / name
    file_storage.save(path)
    return f"properties/{property_id}/{media_type}/{name}"


def _supabase_save(file_storage: FileStorage, property_id, media_type: str, ext: str) -> str:
    client = _supabase_client()
    bucket = supabase_bucket_name()
    _ensure_supabase_bucket(client, bucket)

    object_path = f"properties/{property_id}/{media_type}/{uuid.uuid4().hex[:16]}.{ext}"
    payload = _read_bytes(file_storage)
    if not payload:
        raise RuntimeError("Empty upload payload.")

    content_type = _content_type(file_storage.filename or object_path, media_type, ext)
    storage = client.storage.from_(bucket)
    storage.upload(
        object_path,
        payload,
        file_options={
            "content-type": content_type,
            "upsert": "true",
        },
    )
    public_url = (storage.get_public_url(object_path) or "").strip().rstrip("?")
    if not public_url.startswith("http"):
        base = _env("SUPABASE_URL").rstrip("/")
        public_url = f"{base}/storage/v1/object/public/{bucket}/{object_path}"
    return public_url


def _configure_cloudinary() -> None:
    import cloudinary

    url = _env("CLOUDINARY_URL")
    if url:
        cloudinary.config(cloudinary_url=url, secure=True)
        return
    cloudinary.config(
        cloud_name=_env("CLOUDINARY_CLOUD_NAME"),
        api_key=_env("CLOUDINARY_API_KEY"),
        api_secret=_env("CLOUDINARY_API_SECRET"),
        secure=True,
    )


def _resource_type(media_type: str, ext: str) -> str:
    if media_type == "videos" or ext in {"mp4", "mov", "webm"}:
        return "video"
    if media_type == "documents" or ext == "pdf":
        return "raw"
    return "image"


def _cloudinary_save(file_storage: FileStorage, property_id, media_type: str, ext: str) -> str:
    from cloudinary.uploader import upload as cloudinary_upload

    _configure_cloudinary()
    try:
        file_storage.stream.seek(0)
    except Exception:
        pass
    result = cloudinary_upload(
        file_storage,
        folder=f"jakkash/properties/{property_id}/{media_type}",
        public_id=uuid.uuid4().hex[:16],
        resource_type=_resource_type(media_type, ext),
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

    Backend order (unless STORAGE_BACKEND forces one):
    Supabase Storage (CDN public URL) → Cloudinary → local disk.
    """
    if not file_storage or not getattr(file_storage, "filename", None):
        return None
    filename = secure_filename(file_storage.filename) or file_storage.filename
    if "." not in filename:
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        return None

    pref = storage_backend_preference()
    if pref == "local":
        return _local_save(file_storage, property_id, media_type, ext)

    if _use_supabase_storage():
        try:
            return _supabase_save(file_storage, property_id, media_type, ext)
        except Exception as exc:
            try:
                current_app.logger.warning(
                    "Supabase upload failed (%s); trying next storage backend.", exc
                )
            except Exception:
                pass
            if pref == "supabase":
                raise

    if _use_cloudinary_storage():
        try:
            return _cloudinary_save(file_storage, property_id, media_type, ext)
        except Exception as exc:
            try:
                current_app.logger.warning(
                    "Cloudinary upload failed (%s); using local storage.", exc
                )
            except Exception:
                pass
            if pref == "cloudinary":
                raise

    return _local_save(file_storage, property_id, media_type, ext)


def is_remote_url(path: str | None) -> bool:
    value = (path or "").strip().lower()
    return value.startswith("http://") or value.startswith("https://")
