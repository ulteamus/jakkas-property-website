"""Build embedded templates and public assets for Vercel."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
OUTPUT = ROOT / "api" / "template_store.py"
PUBLIC = ROOT / "public"
API_STATIC = ROOT / "api" / "static"
SEED_DIR = ROOT / "api" / "seed"
LOCAL_UPLOADS = ROOT / "uploads"
LOCAL_DB = ROOT / "data" / "jakkash.db"
SEED_DB = SEED_DIR / "jakkash.db"
STAGED_UPLOADS = ROOT / "static" / "property-uploads"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"""', '\\"""')


def _write_template_store() -> None:
    entries: list[tuple[str, str]] = []
    for path in sorted(TEMPLATES_DIR.rglob("*.html")):
        key = path.relative_to(TEMPLATES_DIR).as_posix()
        entries.append((key, path.read_text(encoding="utf-8")))

    lines = [
        '"""Auto-generated Jinja templates for Vercel serverless runtime."""',
        "from jinja2 import DictLoader",
        "",
        "TEMPLATES = {",
    ]
    for key, content in entries:
        lines.append(f'    "{key}": """{_escape(content)}""",')
    lines.extend(["}", "", "def loader():", "    return DictLoader(TEMPLATES)", ""])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {OUTPUT} with {len(entries)} templates")


def _stage_property_uploads() -> None:
    source = LOCAL_UPLOADS if LOCAL_UPLOADS.exists() and any(LOCAL_UPLOADS.rglob("*")) else STAGED_UPLOADS
    if source is LOCAL_UPLOADS:
        if STAGED_UPLOADS.exists():
            shutil.rmtree(STAGED_UPLOADS)
        shutil.copytree(LOCAL_UPLOADS, STAGED_UPLOADS)
        print(f"Staged property uploads at {STAGED_UPLOADS}")
    elif not STAGED_UPLOADS.exists():
        print("No property uploads found to stage.")


def _copy_seed_db() -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_DB.exists():
        shutil.copy2(LOCAL_DB, SEED_DB)
        print(f"Seeded database snapshot at {SEED_DB}")
    elif SEED_DB.exists():
        print(f"Using existing database snapshot at {SEED_DB}")
    else:
        print("No database snapshot found for Vercel seed.")


def _copy_static() -> None:
    ignore_assets = shutil.ignore_patterns("preview", "__pycache__", "*.pyc", "property-uploads")
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    if API_STATIC.exists():
        shutil.rmtree(API_STATIC)
    shutil.copytree(ROOT / "static", PUBLIC, ignore=ignore_assets)
    shutil.copytree(ROOT / "static", API_STATIC, ignore=ignore_assets)
    print(f"Copied static assets to {PUBLIC} and {API_STATIC}")


def _copy_uploads_to_public() -> None:
    if not STAGED_UPLOADS.exists() or not any(STAGED_UPLOADS.rglob("*")):
        print("No staged uploads found to publish.")
        return

    dest = PUBLIC / "uploads"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(STAGED_UPLOADS, dest)
    print(f"Published uploads to {dest}")


def main() -> None:
    _write_template_store()
    _stage_property_uploads()
    _copy_seed_db()
    _copy_static()
    _copy_uploads_to_public()


if __name__ == "__main__":
    main()
