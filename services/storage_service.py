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


def _supabase_auth_candidates() -> list[tuple[str, str]]:
    """Ordered (env_name, key) for Storage API.

    Prefer classic JWT keys (``eyJ…``). Newer ``sb_secret_*`` values are often
    rejected by supabase-py as "Invalid API key" even when set on Vercel.
    """
    names = (
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
    )
    jwt_first: list[tuple[str, str]] = []
    other: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in names:
        value = _env(name)
        if not value or value in seen:
            continue
        seen.add(value)
        if value.startswith("eyJ"):
            jwt_first.append((name, value))
        else:
            other.append((name, value))
    return jwt_first + other


def supabase_configured() -> bool:
    return bool(_env("SUPABASE_URL") and _supabase_auth_candidates())


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


def _log_storage(level: str, message: str, *args) -> None:
    try:
        logger = current_app.logger
    except Exception:
        return
    getattr(logger, level, logger.warning)(message, *args)


def _supabase_client(api_key: str | None = None):
    from supabase import create_client

    url = _env("SUPABASE_URL").rstrip("/")
    key = (api_key or "").strip()
    if not key:
        candidates = _supabase_auth_candidates()
        if not candidates:
            raise RuntimeError("Supabase credentials are not configured.")
        key = candidates[0][1]
    if not url or not key:
        raise RuntimeError("Supabase credentials are not configured.")
    return create_client(url, key)


def _is_auth_failure(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "invalid api key",
            "invalid jwt",
            "jwt expired",
            "not authorized",
            "unauthorized",
            "401",
            "403",
        )
    )


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


def _supabase_save_with_client(
    client,
    file_storage: FileStorage,
    property_id,
    media_type: str,
    ext: str,
    key_name: str,
) -> str:
    bucket = supabase_bucket_name()
    _ensure_supabase_bucket(client, bucket)

    object_path = f"properties/{property_id}/{media_type}/{uuid.uuid4().hex[:16]}.{ext}"
    payload = _read_bytes(file_storage)
    if not payload:
        raise RuntimeError("Empty upload payload.")

    content_type = _content_type(file_storage.filename or object_path, media_type, ext)
    storage = client.storage.from_(bucket)
    try:
        storage.upload(
            object_path,
            payload,
            file_options={
                "content-type": content_type,
                "upsert": "true",
            },
        )
    except Exception as exc:
        _log_storage(
            "error",
            "Supabase upload failed provider=supabase bucket=%s key_env=%s path=%s reason=%s",
            bucket,
            key_name,
            object_path,
            exc,
        )
        raise

    public_url = (storage.get_public_url(object_path) or "").strip().rstrip("?")
    if not public_url.startswith("http"):
        base = _env("SUPABASE_URL").rstrip("/")
        public_url = f"{base}/storage/v1/object/public/{bucket}/{object_path}"
    if not public_url.startswith("http"):
        raise RuntimeError("Supabase upload returned no public HTTPS URL.")
    _log_storage(
        "info",
        "Supabase upload ok provider=supabase bucket=%s key_env=%s",
        bucket,
        key_name,
    )
    return public_url


def _supabase_save(file_storage: FileStorage, property_id, media_type: str, ext: str) -> str:
    candidates = _supabase_auth_candidates()
    if not candidates:
        raise RuntimeError("Supabase credentials are not configured.")

    last_exc: Exception | None = None
    for key_name, api_key in candidates:
        try:
            client = _supabase_client(api_key)
            return _supabase_save_with_client(
                client, file_storage, property_id, media_type, ext, key_name
            )
        except Exception as exc:
            last_exc = exc
            if _is_auth_failure(exc) and (key_name, api_key) != candidates[-1]:
                _log_storage(
                    "warning",
                    "Supabase auth failed with %s (%s); trying next configured key.",
                    key_name,
                    exc,
                )
                try:
                    file_storage.stream.seek(0)
                except Exception:
                    pass
                continue
            raise
    raise RuntimeError(
        f"Supabase storage auth failed for all configured keys: {last_exc}"
    ) from last_exc


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


def _forbid_ephemeral_disk() -> bool:
    """Vercel / explicit supabase backend must never write ephemeral container disk."""
    if storage_backend_preference() == "supabase":
        return True
    return bool((os.getenv("VERCEL") or "").strip())


def save_media(file_storage, property_id, media_type, allowed) -> str | None:
    """
    Persist an uploaded file.

    Backend order (unless STORAGE_BACKEND forces one):
    Supabase Storage (CDN public URL) → Cloudinary → local disk.
    On Vercel or STORAGE_BACKEND=supabase, local disk is forbidden.
    """
    if not file_storage or not getattr(file_storage, "filename", None):
        _log_storage("warning", "save_media skipped: empty file or missing filename")
        return None
    filename = secure_filename(file_storage.filename) or file_storage.filename
    if "." not in filename:
        _log_storage("warning", "save_media rejected: no extension on %r", filename)
        return None
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        _log_storage(
            "warning",
            "save_media rejected: extension %r not in allowed=%s",
            ext,
            sorted(allowed),
        )
        return None

    pref = storage_backend_preference()
    if pref == "local":
        if _forbid_ephemeral_disk():
            raise RuntimeError(
                "Local disk storage is disabled on Vercel; configure Supabase Storage."
            )
        return _local_save(file_storage, property_id, media_type, ext)

    if _use_supabase_storage():
        try:
            url = _supabase_save(file_storage, property_id, media_type, ext)
            if _forbid_ephemeral_disk() and not is_remote_url(url):
                raise RuntimeError(
                    "Supabase returned a non-remote path; refusing ephemeral media on Vercel."
                )
            return url
        except Exception as exc:
            _log_storage(
                "warning",
                "Supabase upload failed (provider=supabase status=error reason=%s); "
                "trying next storage backend.",
                exc,
            )
            if pref == "supabase" or _forbid_ephemeral_disk():
                raise

    if _use_cloudinary_storage():
        try:
            url = _cloudinary_save(file_storage, property_id, media_type, ext)
            if _forbid_ephemeral_disk() and not is_remote_url(url):
                raise RuntimeError(
                    "Cloudinary returned a non-remote path; refusing ephemeral media on Vercel."
                )
            return url
        except Exception as exc:
            _log_storage(
                "warning",
                "Cloudinary upload failed (provider=cloudinary status=error reason=%s); "
                "falling back if allowed.",
                exc,
            )
            if pref == "cloudinary" or _forbid_ephemeral_disk():
                raise

    if _forbid_ephemeral_disk():
        raise RuntimeError(
            "No cloud storage backend available; refusing ephemeral local upload. "
            "Check Vercel env: SUPABASE_URL, SUPABASE_KEY (JWT service role), "
            "SUPABASE_BUCKET, STORAGE_BACKEND=supabase."
        )
    return _local_save(file_storage, property_id, media_type, ext)


def is_remote_url(path: str | None) -> bool:
    value = (path or "").strip().lower()
    return value.startswith("http://") or value.startswith("https://")


def _supabase_object_path_from_url(url: str) -> str | None:
    bucket = supabase_bucket_name()
    marker = f"/storage/v1/object/public/{bucket}/"
    if marker not in url:
        return None
    return url.split(marker, 1)[-1].split("?", 1)[0].strip() or None


def _cloudinary_public_id_from_url(url: str) -> tuple[str | None, str]:
    """Return (public_id, resource_type) best-effort from a Cloudinary delivery URL."""
    try:
        # .../image/upload/v123/folder/name.ext or /video/upload/ /raw/upload/
        resource_type = "image"
        if "/video/upload/" in url:
            resource_type = "video"
        elif "/raw/upload/" in url:
            resource_type = "raw"
        parts = url.split("/upload/", 1)
        if len(parts) != 2:
            return None, resource_type
        rest = parts[1].split("?", 1)[0]
        # drop optional version segment v123/
        segs = [s for s in rest.split("/") if s]
        if segs and segs[0].startswith("v") and segs[0][1:].isdigit():
            segs = segs[1:]
        if not segs:
            return None, resource_type
        last = segs[-1]
        if "." in last:
            segs[-1] = last.rsplit(".", 1)[0]
        return "/".join(segs), resource_type
    except Exception:
        return None, "image"


def delete_media(path: str | None) -> bool:
    """Best-effort delete of a stored media object. Never raises to callers."""
    value = (path or "").strip()
    if not value:
        return False
    try:
        if is_remote_url(value):
            if supabase_configured() and "/storage/v1/object/public/" in value:
                object_path = _supabase_object_path_from_url(value)
                if object_path:
                    try:
                        client = _supabase_client()
                        client.storage.from_(supabase_bucket_name()).remove([object_path])
                        return True
                    except Exception:
                        pass
            if cloudinary_configured() and "res.cloudinary.com" in value:
                public_id, resource_type = _cloudinary_public_id_from_url(value)
                if public_id:
                    try:
                        from cloudinary.uploader import destroy as cloudinary_destroy

                        _configure_cloudinary()
                        cloudinary_destroy(public_id, resource_type=resource_type)
                        return True
                    except Exception:
                        pass
            return False

        # Local relative path under UPLOAD_ROOT / property-uploads
        try:
            root = Path(current_app.config["UPLOAD_ROOT"])
            rel = value.lstrip("/").replace("\\", "/")
            candidates = [
                root / rel,
                Path(current_app.root_path) / "static" / "property-uploads" / rel,
            ]
            if rel.startswith("properties/"):
                candidates.insert(0, root / rel[len("properties/") :])
            for candidate in candidates:
                try:
                    if candidate.is_file():
                        candidate.unlink()
                        return True
                except Exception:
                    continue
        except Exception:
            return False
        return False
    except Exception:
        return False
