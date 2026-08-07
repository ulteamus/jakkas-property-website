"""Assign luxury-pool photos to available properties missing images (no CRM deletes)."""
from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from PIL import Image

from app import create_app
from database import execute, query_all
from models import property as prop_model

POOL_DIR = BASE_DIR / "static" / "img" / "luxury-pool"
UPLOADS = BASE_DIR / "uploads" / "properties"
STAGED = BASE_DIR / "static" / "property-uploads" / "properties"
DEFAULT_JPG = BASE_DIR / "static" / "img" / "default-property.jpg"

# Paths previously referenced on the live detail page (ensure files exist).
LEGACY_LIVE_PATHS = [
    "properties/63/images/f1cd38b29823.png",
    "properties/63/images/cec6e0950109.png",
]


def _pool_files() -> list[Path]:
    files = sorted(POOL_DIR.glob("luxury-*.jpg"))
    if not files and DEFAULT_JPG.exists():
        files = [DEFAULT_JPG]
    if not files:
        raise SystemExit("No luxury-pool images found.")
    return files


def _write_image(dest: Path, src: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix.lower() == ".png" and src.suffix.lower() != ".png":
        Image.open(src).convert("RGB").save(dest, format="PNG", optimize=True)
    else:
        shutil.copy2(src, dest)


def _mirror_to_staged(rel: str, src_file: Path) -> None:
    # rel like properties/63/images/x.jpg
    parts = rel.replace("\\", "/").split("/")
    if parts[0] != "properties":
        return
    dest = STAGED.joinpath(*parts[1:])
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or dest.stat().st_size < 100:
        shutil.copy2(src_file, dest)


def ensure_legacy_files(pool: list[Path]) -> None:
    for i, rel in enumerate(LEGACY_LIVE_PATHS):
        src = pool[i % len(pool)]
        local = BASE_DIR / "uploads" / rel
        _write_image(local, src)
        _mirror_to_staged(rel, local)
        print(f"legacy file ready: {rel}")


def assign_property_photos(property_id: int, title: str, pool: list[Path], count: int = 4) -> str:
    media = prop_model.get_media(property_id) or {}
    existing = media.get("images") or []
    if existing:
        primary = None
        for row in existing:
            fp = (row.get("file_path") or "").strip()
            if not fp:
                continue
            local = BASE_DIR / "uploads" / fp
            if not local.exists():
                _write_image(local, pool[0])
            _mirror_to_staged(fp, local)
            if row.get("is_primary") or primary is None:
                primary = fp
        if primary:
            execute("UPDATE properties SET primary_image=%s WHERE id=%s", (primary, property_id))
            return primary

    primary_rel = None
    for i in range(count):
        src = pool[(property_id + i) % len(pool)]
        name = f"{uuid.uuid4().hex[:12]}.jpg"
        rel = f"properties/{property_id}/images/{name}"
        local = BASE_DIR / "uploads" / rel
        _write_image(local, src)
        _mirror_to_staged(rel, local)
        prop_model.add_image(property_id, rel, is_primary=(i == 0), sort_order=i)
        if i == 0:
            primary_rel = rel
            execute("UPDATE properties SET primary_image=%s WHERE id=%s", (primary_rel, property_id))
    print(f"seeded {count} images for #{property_id} {title}")
    return primary_rel or ""


def main() -> None:
    pool = _pool_files()
    ensure_legacy_files(pool)
    # Also guarantee default placeholder exists in staged uploads tree root for sanity.
    if DEFAULT_JPG.exists():
        for dest in (
            BASE_DIR / "static" / "img" / "placeholder.jpg",
            BASE_DIR / "api" / "static" / "img" / "default-property.jpg",
        ):
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(DEFAULT_JPG, dest)

    app = create_app()
    with app.app_context():
        props = query_all(
            "SELECT id, property_name, primary_image FROM properties WHERE status='available' ORDER BY id"
        )
        for p in props:
            assign_property_photos(int(p["id"]), p.get("property_name") or "", pool, count=4)

        # Special-case: if #63 still has no rows but legacy files exist, register them.
        media63 = prop_model.get_media(63) or {}
        if not (media63.get("images") or []):
            for i, rel in enumerate(LEGACY_LIVE_PATHS):
                prop_model.add_image(63, rel, is_primary=(i == 0), sort_order=i)
            execute(
                "UPDATE properties SET primary_image=%s WHERE id=%s",
                (LEGACY_LIVE_PATHS[0], 63),
            )
            print("registered legacy paths for property 63")

    print("done")


if __name__ == "__main__":
    main()
