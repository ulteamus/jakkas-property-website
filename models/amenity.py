import re

from flask import g, has_app_context

from database import execute, query_all, query_one

DEFAULT_AMENITIES = [
    "Parking",
    "Lift",
    "Security",
    "Power Backup",
    "Garden",
    "Gym",
    "Swimming Pool",
    "Club House",
    "CCTV",
    "Water Supply",
]

MAX_LABEL_LEN = 60
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 &/().,'+-]*$")
_CACHE_KEY = "_jk_active_amenity_labels"


def slugify_amenity(label):
    slug = re.sub(r"[^a-z0-9]+", "_", (label or "").strip().lower()).strip("_")
    return slug[:80]


def normalize_label(label):
    return re.sub(r"\s+", " ", (label or "").strip())


def validate_label(label, exclude_id=None):
    """Return (clean_label, slug) or raise ValueError."""
    clean = normalize_label(label)
    if not clean:
        raise ValueError("Amenity name is required.")
    if len(clean) > MAX_LABEL_LEN:
        raise ValueError(f"Amenity name must be at most {MAX_LABEL_LEN} characters.")
    if not _LABEL_RE.match(clean):
        raise ValueError("Amenity name contains unsupported characters.")
    slug = slugify_amenity(clean)
    if not slug:
        raise ValueError("Amenity name must contain letters or numbers.")
    for row in list_all():
        if exclude_id is not None and int(row.get("id") or 0) == int(exclude_id):
            continue
        if (row.get("slug") or "") == slug or (row.get("label") or "").strip().lower() == clean.lower():
            raise ValueError(f"Amenity '{clean}' already exists.")
    return clean, slug


def _clear_cache():
    if has_app_context():
        g.pop(_CACHE_KEY, None)


def list_all():
    try:
        rows = query_all(
            "SELECT id, slug, label, is_active, sort_order FROM amenities ORDER BY sort_order, label"
        )
    except Exception:
        return []
    return [dict(r) for r in rows or []]


def list_active_labels():
    """Active amenity labels for forms; falls back to defaults when the table is missing/empty."""
    if has_app_context() and _CACHE_KEY in g:
        return list(g.get(_CACHE_KEY))
    rows = [r for r in list_all() if int(r.get("is_active") or 0)]
    labels = [r["label"] for r in rows if r.get("label")] or list(DEFAULT_AMENITIES)
    if has_app_context():
        setattr(g, _CACHE_KEY, labels)
    return list(labels)


def labels_for_form(selected=None):
    """Active labels plus any already-selected values so saving never drops them."""
    labels = list_active_labels()
    lowered = {label.lower() for label in labels}
    if isinstance(selected, str):
        selected = [part for part in selected.split(",")]
    for value in selected or []:
        text = normalize_label(str(value))
        if text and text.lower() not in lowered:
            labels.append(text)
            lowered.add(text.lower())
    return labels


def get(amenity_id):
    try:
        row = query_one(
            "SELECT id, slug, label, is_active, sort_order FROM amenities WHERE id=%s",
            (amenity_id,),
        )
    except Exception:
        return None
    return dict(row) if row else None


def _next_sort_order():
    try:
        row = query_one("SELECT COALESCE(MAX(sort_order), 0) AS m FROM amenities")
    except Exception:
        return 10
    return int((row or {}).get("m") or 0) + 10


def create(label, sort_order=None):
    clean, slug = validate_label(label)
    order = int(sort_order) if sort_order not in (None, "") else _next_sort_order()
    execute(
        """INSERT INTO amenities (slug, label, is_active, sort_order)
           VALUES (%s, %s, %s, %s)
           ON CONFLICT (slug) DO NOTHING""",
        (slug, clean, True, order),
    )
    _clear_cache()
    row = query_one("SELECT id FROM amenities WHERE slug=%s", (slug,))
    return int(row["id"]) if row else None


def update(amenity_id, label, sort_order=None):
    existing = get(amenity_id)
    if not existing:
        raise ValueError("Amenity not found.")
    clean, _slug = validate_label(label, exclude_id=amenity_id)
    order = int(sort_order) if sort_order not in (None, "") else int(existing.get("sort_order") or 0)
    execute(
        "UPDATE amenities SET label=%s, sort_order=%s WHERE id=%s",
        (clean, order, amenity_id),
    )
    _clear_cache()
    return get(amenity_id)


def toggle(amenity_id):
    existing = get(amenity_id)
    if not existing:
        raise ValueError("Amenity not found.")
    new_value = not bool(int(existing.get("is_active") or 0))
    execute("UPDATE amenities SET is_active=%s WHERE id=%s", (new_value, amenity_id))
    _clear_cache()
    return new_value
