import json
import math
import uuid
from database import execute, query_all, query_one
from database.db import skip_runtime_ddl, use_sqlite
from utils.helpers import slugify


TYPE_ALIASES = {
    "apartment": ["apartment", "flat"],
    "flat": ["flat", "apartment"],
    "villa": ["villa", "bungalow"],
    "bungalow": ["bungalow", "villa"],
    "commercial": ["commercial", "shop", "office"],
    "residential": ["residential", "apartment", "flat", "villa", "bungalow", "plot"],
    "shop": ["shop", "commercial"],
    "office": ["office", "commercial"],
    "plot": ["plot", "residential"],
}

_schema_checked = False


def _ensure_schema():
    global _schema_checked
    if _schema_checked:
        return
    _schema_checked = True
    if skip_runtime_ddl():
        return
    from database.db import get_connection, use_sqlite

    get_connection()
    extra_sqlite = {
        "owner_admin_id": "INTEGER",
        "creation_source": "TEXT DEFAULT 'admin'",
        "block_wing": "TEXT",
        "unit_number": "TEXT",
        "listing_intent": "TEXT DEFAULT 'sell'",
        "seller_type": "TEXT",
        "is_active": "INTEGER DEFAULT 1",
        "approval_status": "TEXT DEFAULT 'approved'",
    }
    extra_mysql = {
        "owner_admin_id": "INT NULL",
        "creation_source": "VARCHAR(40) DEFAULT 'admin'",
        "block_wing": "VARCHAR(40)",
        "unit_number": "VARCHAR(80)",
        "listing_intent": "VARCHAR(20) DEFAULT 'sell'",
        "seller_type": "VARCHAR(20)",
        "is_active": "TINYINT(1) DEFAULT 1",
        "approval_status": "VARCHAR(30) DEFAULT 'approved'",
    }
    if use_sqlite():
        cols = {str(row.get("name", "")).lower() for row in query_all("PRAGMA table_info(properties)")}
        for name, ddl in extra_sqlite.items():
            if name not in cols:
                execute(f"ALTER TABLE properties ADD COLUMN {name} {ddl}")
        return
    cols = {str(row.get("Field", "")).lower() for row in query_all("SHOW COLUMNS FROM properties")}
    for name, ddl in extra_mysql.items():
        if name not in cols:
            execute(f"ALTER TABLE properties ADD COLUMN {name} {ddl}")


OWNER_PUBLIC_STRIP_KEYS = (
    "owner_name",
    "owner_phone",
    "owner_email",
    "owner_contact",
    "owner_mobile",
    "owner_alt_mobile",
    "owner_address",
    "bungalow_number",
    "owner_admin_id",
)


def _parse(row):
    if not row:
        return None
    if row.get("amenities") and isinstance(row["amenities"], str):
        try:
            row["amenities"] = json.loads(row["amenities"])
        except json.JSONDecodeError:
            row["amenities"] = []
    listing_type = (row.get("listing_type") or "sale").lower()
    intent = (row.get("listing_intent") or "").strip().lower()
    if intent not in {"sell", "rent"}:
        if listing_type == "rent":
            intent = "rent"
        elif listing_type in {"sell", "sale", "buy"}:
            intent = "sell"
        else:
            intent = "sell"
    row["listing_intent"] = intent
    row["seller_type"] = _normalize_seller_type(row.get("seller_type"))
    row["block_wing"] = (row.get("block_wing") or "").strip() or None
    row["unit_number"] = (row.get("unit_number") or "").strip() or None
    row["display_type"] = _display_type(row.get("property_type"))
    row["creation_source"] = _normalize_creation_source(row.get("creation_source"))
    return row


def _public_locality_address(area_name):
    """General locality only — never street, building, or unit detail."""
    area = (area_name or "").strip()
    if not area:
        return "Surat"
    if area.lower() == "surat":
        return "Surat"
    return f"{area}, Surat"


def _mask_coordinate(value):
    """Round to 2 decimal places (~1.1km) for public map markers."""
    if value is None or value == "":
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


# Public fallback when primary_image is missing or blank (served from static/).
DEFAULT_PROPERTY_IMAGE_URL = "/static/img/default-property.jpg"


def public_image_url(path, external=False):
    """Build a browser URL for a stored upload path, remote URL, or the default placeholder."""
    raw = (path or "").strip()
    if not raw:
        url = DEFAULT_PROPERTY_IMAGE_URL
    elif raw.startswith(("http://", "https://")):
        # Supabase CDN / Cloudinary / any absolute URL — return unchanged.
        url = raw.rstrip("?")
    else:
        rel = raw.replace("\\", "/").lstrip("/")
        # Keys already prefixed with the public bucket name.
        if rel.startswith("property-images/") or rel.startswith("properties/storage/"):
            from config import SUPABASE_BUCKET, SUPABASE_URL

            if SUPABASE_URL:
                if rel.startswith(f"{SUPABASE_BUCKET}/"):
                    url = f"{SUPABASE_URL}/storage/v1/object/public/{rel}"
                else:
                    url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{rel}"
            else:
                url = f"/uploads/{rel}"
        elif rel.startswith("static/") or rel.startswith("img/"):
            url = f"/{rel}" if not rel.startswith("/") else rel
        elif rel.startswith("/static/") or rel.startswith("/uploads/"):
            url = rel if rel.startswith("/") else f"/{rel}"
        else:
            # Legacy local relative paths (properties/<id>/images/...).
            url = f"/uploads/{rel}"

    if external and url.startswith("/"):
        try:
            from flask import has_request_context, request

            if has_request_context():
                return request.url_root.rstrip("/") + url
        except Exception:
            pass
    return url


def to_dict(row, public=True):
    """
    Serialize a property row for API/templates.

    public=True (default): locality-only address, rounded coords, owner fields omitted.
    public=False: full CRM record for admin routes.
    """
    if not row:
        return None
    data = dict(row)
    if data.get("amenities") and isinstance(data["amenities"], str):
        try:
            data["amenities"] = json.loads(data["amenities"])
        except json.JSONDecodeError:
            data["amenities"] = []
    if "listing_intent" not in data or "display_type" not in data:
        parsed = _parse(dict(data))
        if parsed:
            data = parsed
    primary = (data.get("primary_image") or "").strip() or None
    data["primary_image"] = primary
    data["primary_image_url"] = public_image_url(primary)
    if not public:
        return data
    data["address"] = _public_locality_address(data.get("area_name"))
    data["latitude"] = _mask_coordinate(data.get("latitude"))
    data["longitude"] = _mask_coordinate(data.get("longitude"))
    for key in OWNER_PUBLIC_STRIP_KEYS:
        data.pop(key, None)
    return data


def to_dict_list(rows, public=True):
    return [to_dict(row, public=public) for row in (rows or [])]


def _display_type(property_type):
    if not property_type:
        return "Property"
    mapping = {
        "flat": "Flat",
        "apartment": "Apartment",
        "villa": "Villa",
        "bungalow": "Bungalow",
        "plot": "Plot",
        "shop": "Commercial",
        "office": "Commercial",
        "commercial": "Commercial",
        "residential": "Residential",
    }
    return mapping.get(property_type.lower(), property_type.replace("_", " ").title())


def _normalize_listing_type(value):
    listing_type = (value or "sale").strip().lower()
    if listing_type in {"rent", "rental"}:
        return "rent"
    if listing_type in {"sell", "sale", "buy"}:
        return "sale"
    return "sale"


def _normalize_listing_intent(value, listing_type=None):
    intent = (value or "").strip().lower()
    if intent in {"sell", "rent"}:
        return intent
    lt = _normalize_listing_type(listing_type or value)
    return "rent" if lt == "rent" else "sell"


def _normalize_seller_type(value):
    cleaned = (value or "").strip().lower()
    if cleaned in {"owner", "broker", "developer"}:
        return cleaned
    return None


def _normalize_creation_source(value):
    cleaned = (value or "admin").strip().lower()
    if cleaned in {"user_submission", "user", "public"}:
        return "user_submission"
    return "admin"


def _expand_property_types(property_type):
    if not property_type:
        return []
    p_type = property_type.strip().lower()
    return TYPE_ALIASES.get(p_type, [p_type])


def _normalize_property_type(value):
    p_type = (value or "flat").strip().lower()
    mapping = {
        "apartment": "flat",
        "villa": "bungalow",
        "commercial": "shop",
        "residential": "flat",
    }
    return mapping.get(p_type, p_type)


def _haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dlat = math.radians(float(lat2) - float(lat1))
    dlng = math.radians(float(lng2) - float(lng1))
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def get_by_id(pid, owner_admin_id=None):
    _ensure_schema()
    if owner_admin_id:
        return _parse(
            query_one(
                "SELECT * FROM properties WHERE id=%s AND owner_admin_id=%s",
                (pid, owner_admin_id),
            )
        )
    return _parse(query_one("SELECT * FROM properties WHERE id=%s", (pid,)))


def get_by_slug(slug):
    _ensure_schema()
    return _parse(query_one("SELECT * FROM properties WHERE slug=%s", (slug,)))


def find_duplicate(property_name, address, area_name=None, price=None, exclude_id=None):
    _ensure_schema()
    sql = (
        "SELECT id, property_name, slug FROM properties "
        "WHERE LOWER(property_name)=LOWER(%s) "
        "AND LOWER(IFNULL(address,''))=LOWER(IFNULL(%s,''))"
    )
    params = [property_name or "", address or ""]
    if area_name:
        sql += " AND LOWER(IFNULL(area_name,''))=LOWER(IFNULL(%s,''))"
        params.append(area_name)
    if price is not None:
        sql += " AND ABS(price-%s) <= 1"
        params.append(float(price))
    if exclude_id:
        sql += " AND id!=%s"
        params.append(int(exclude_id))
    sql += " LIMIT 1"
    return query_one(sql, params)


def search(area=None, property_type=None, min_price=None, max_price=None,
           bhk=None, status="available", keyword=None, featured_only=False,
           sort="newest", limit=100, offset=0, all_statuses=False,
           listing_intent=None, min_sq_ft=None, max_sq_ft=None,
           city=None, location=None, property_id=None, owner_admin_id=None):
    _ensure_schema()
    sql = "SELECT * FROM properties WHERE 1=1"
    params = []
    if not all_statuses and status:
        sql += " AND status=%s"
        params.append(status)

    area_filter = area or location or city
    if area_filter:
        sql += " AND (area_name LIKE %s OR address LIKE %s)"
        params.extend([f"%{area_filter}%", f"%{area_filter}%"])

    if property_type:
        property_types = _expand_property_types(property_type)
        placeholders = ",".join(["%s"] * len(property_types))
        sql += f" AND LOWER(property_type) IN ({placeholders})"
        params.extend(property_types)

    if min_price is not None:
        sql += " AND price >= %s"
        params.append(min_price)
    if max_price is not None:
        sql += " AND price <= %s"
        params.append(max_price)
    if min_sq_ft is not None:
        sql += " AND sq_ft >= %s"
        params.append(min_sq_ft)
    if max_sq_ft is not None:
        sql += " AND sq_ft <= %s"
        params.append(max_sq_ft)
    if bhk is not None:
        sql += " AND bhk >= %s"
        params.append(bhk)
    if property_id:
        sql += " AND id=%s"
        params.append(property_id)
    if owner_admin_id:
        sql += " AND owner_admin_id=%s"
        params.append(owner_admin_id)
    if featured_only:
        sql += " AND is_featured=1"

    if listing_intent:
        intent = listing_intent.lower()
        if intent == "rent":
            sql += " AND listing_type='rent'"
        elif intent in {"buy", "sell", "sale"}:
            sql += " AND listing_type!='rent'"

    if keyword:
        sql += (
            " AND (property_name LIKE %s OR description LIKE %s "
            "OR area_name LIKE %s OR address LIKE %s OR slug LIKE %s)"
        )
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw, kw, kw])

    order = {
        "price_asc": "price ASC",
        "price_desc": "price DESC",
        "newest": "created_at DESC",
        "views": "view_count DESC",
    }.get(sort, "created_at DESC")
    sql += f" ORDER BY {order} LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    rows = [_parse(r) for r in query_all(sql, params)]
    forced_intent = (listing_intent or "").lower()
    if forced_intent in {"buy", "sell", "rent"}:
        for row in rows:
            row["listing_intent"] = forced_intent
    return rows


def featured(limit=6):
    _ensure_schema()
    return search(featured_only=True, limit=limit)


def latest(limit=8):
    _ensure_schema()
    return search(limit=limit)


def map_markers(public=True):
    _ensure_schema()
    rows = query_all(
        """SELECT id, property_name, area_name, price, property_type,
                  latitude, longitude, primary_image, slug, bhk, sq_ft
           FROM properties WHERE status='available' AND latitude IS NOT NULL"""
    )
    return to_dict_list(rows, public=public)


def create(data, created_by_admin_id=None):
    _ensure_schema()
    slug = data.get("slug") or slugify(data["property_name"])
    if query_one("SELECT id FROM properties WHERE slug=%s", (slug,)):
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    property_type = _normalize_property_type(data["property_type"])
    amenities = json.dumps(data.get("amenities") or [])
    listing_intent = _normalize_listing_intent(
        data.get("listing_intent"), data.get("listing_type", "sale")
    )
    listing_type = "rent" if listing_intent == "rent" else _normalize_listing_type(
        data.get("listing_type", "sale")
    )
    if listing_intent == "rent":
        listing_type = "rent"
    creation_source = _normalize_creation_source(data.get("creation_source"))
    seller_type = _normalize_seller_type(data.get("seller_type"))
    block_wing = (data.get("block_wing") or "").strip() or None
    unit_number = (data.get("unit_number") or "").strip() or None
    pid = execute(
        """INSERT INTO properties
           (property_name,slug,property_type,area_name,address,price,bhk,sq_ft,
            description,amenities,latitude,longitude,status,is_featured,listing_type,primary_image,owner_admin_id,creation_source,
            block_wing,unit_number,listing_intent,seller_type)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            data["property_name"], slug, property_type, data["area_name"],
            data.get("address"), data["price"], data.get("bhk", 0), data["sq_ft"],
            data.get("description"), amenities, data.get("latitude", 21.1702),
            data.get("longitude", 72.8311), data.get("status", "available"),
            bool(data.get("is_featured")), listing_type,
            data.get("primary_image"), created_by_admin_id or _default_owner_admin_id(), creation_source,
            block_wing, unit_number, listing_intent, seller_type,
        ),
    )
    return get_by_id(pid)


def _default_owner_admin_id():
    from models.admin import Admin

    return Admin.get_default_owner_admin_id()


def update(pid, data):
    _ensure_schema()
    property_type = _normalize_property_type(data["property_type"])
    amenities = json.dumps(data.get("amenities") or [])
    listing_intent = _normalize_listing_intent(
        data.get("listing_intent"), data.get("listing_type", "sale")
    )
    listing_type = "rent" if listing_intent == "rent" else _normalize_listing_type(
        data.get("listing_type", "sale")
    )
    if listing_intent == "rent":
        listing_type = "rent"
    seller_type = _normalize_seller_type(data.get("seller_type"))
    block_wing = (data.get("block_wing") or "").strip() or None
    unit_number = (data.get("unit_number") or "").strip() or None
    execute(
        """UPDATE properties SET property_name=%s,property_type=%s,area_name=%s,address=%s,
           price=%s,bhk=%s,sq_ft=%s,description=%s,amenities=%s,latitude=%s,longitude=%s,
           status=%s,is_featured=%s,listing_type=%s,block_wing=%s,unit_number=%s,
           listing_intent=%s,seller_type=%s WHERE id=%s""",
        (
            data["property_name"], property_type, data["area_name"],
            data.get("address"), data["price"], data.get("bhk", 0), data["sq_ft"],
            data.get("description"), amenities, data.get("latitude"),
            data.get("longitude"), data.get("status"), bool(data.get("is_featured")),
            listing_type, block_wing, unit_number, listing_intent, seller_type, pid,
        ),
    )


def delete(pid):
    _ensure_schema()
    execute("DELETE FROM properties WHERE id=%s", (pid,))


def set_status(pid, status):
    _ensure_schema()
    execute("UPDATE properties SET status=%s WHERE id=%s", (status, pid))


def publish_approved(pid):
    """
    Mark a listing live for the public panel.
    Always sets status='available'. Best-effort also sets is_active / approval_status
    when those columns exist (never fails the approve flow if they do not).
    """
    _ensure_schema()
    execute("UPDATE properties SET status=%s WHERE id=%s", ("available", pid))
    try:
        execute(
            "UPDATE properties SET is_active=%s, approval_status=%s WHERE id=%s",
            (True, "approved", pid),
        )
    except Exception:
        pass


def increment_views(pid):
    _ensure_schema()
    execute("UPDATE properties SET view_count=view_count+1 WHERE id=%s", (pid,))


def similar(pid, limit=4):
    _ensure_schema()
    p = get_by_id(pid)
    if not p:
        return []
    price = float(p["price"])
    return [_parse(r) for r in query_all(
        """SELECT * FROM properties WHERE id!=%s AND status='available'
           AND (area_name=%s OR property_type=%s) AND price BETWEEN %s AND %s
           ORDER BY ABS(price-%s) LIMIT %s""",
        (pid, p["area_name"], p["property_type"], price * 0.7, price * 1.3,
         price, limit),
    )]


def get_media(pid):
    _ensure_schema()
    return {
        "images": query_all(
            "SELECT * FROM property_images WHERE property_id=%s ORDER BY sort_order,is_primary DESC",
            (pid,),
        ),
        "videos": query_all(
            "SELECT * FROM property_videos WHERE property_id=%s ORDER BY sort_order", (pid,)
        ),
        "documents": query_all(
            "SELECT * FROM property_documents WHERE property_id=%s ORDER BY uploaded_at DESC", (pid,)
        ),
    }


def get_media_bulk(pids):
    _ensure_schema()
    ids = [int(x) for x in pids if x]
    if not ids:
        return {}
    placeholder = ",".join(["%s"] * len(ids))
    images = query_all(
        f"""SELECT property_id, file_path, is_primary, sort_order
            FROM property_images WHERE property_id IN ({placeholder})
            ORDER BY property_id, sort_order, is_primary DESC""",
        tuple(ids),
    )
    videos = query_all(
        f"""SELECT property_id, file_path, title, sort_order
            FROM property_videos WHERE property_id IN ({placeholder})
            ORDER BY property_id, sort_order""",
        tuple(ids),
    )
    media_map = {pid: {"images": [], "videos": []} for pid in ids}
    for row in images:
        media_map.setdefault(row["property_id"], {"images": [], "videos": []})["images"].append(row)
    for row in videos:
        media_map.setdefault(row["property_id"], {"images": [], "videos": []})["videos"].append(row)
    return media_map


def add_image(pid, path, is_primary=False, sort_order=0):
    _ensure_schema()
    if is_primary:
        execute("UPDATE property_images SET is_primary=0 WHERE property_id=%s", (pid,))
        execute("UPDATE properties SET primary_image=%s WHERE id=%s", (path, pid))
    execute(
        "INSERT INTO property_images (property_id,file_path,is_primary,sort_order) VALUES (%s,%s,%s,%s)",
        (pid, path, bool(is_primary), sort_order),
    )


def add_video(pid, path, title=None, sort_order=0):
    _ensure_schema()
    execute(
        "INSERT INTO property_videos (property_id,file_path,title,sort_order) VALUES (%s,%s,%s,%s)",
        (pid, path, title, sort_order),
    )


def add_document(pid, path, doc_name=None):
    _ensure_schema()
    execute(
        "INSERT INTO property_documents (property_id,file_path,doc_name) VALUES (%s,%s,%s)",
        (pid, path, doc_name or "Document"),
    )


def areas_list():
    _ensure_schema()
    rows = query_all(
        "SELECT DISTINCT area_name FROM properties WHERE status='available' ORDER BY area_name"
    )
    return [r["area_name"] for r in rows]


def categories_summary():
    _ensure_schema()
    rows = query_all(
        """SELECT property_type, COUNT(*) AS total
           FROM properties WHERE status='available'
           GROUP BY property_type ORDER BY total DESC"""
    )
    category_counts = {
        "Apartment": 0,
        "Flat": 0,
        "Villa": 0,
        "Bungalow": 0,
        "Plot": 0,
        "Commercial": 0,
        "Residential": 0,
    }

    for row in rows:
        p_type = (row.get("property_type") or "").lower()
        total = int(row.get("total") or 0)
        if p_type in {"shop", "office", "commercial"}:
            category_counts["Commercial"] += total
        elif p_type in {"apartment"}:
            category_counts["Apartment"] += total
        elif p_type in {"flat"}:
            category_counts["Flat"] += total
        elif p_type in {"villa"}:
            category_counts["Villa"] += total
        elif p_type in {"bungalow"}:
            category_counts["Bungalow"] += total
        elif p_type in {"plot"}:
            category_counts["Plot"] += total
        else:
            category_counts["Residential"] += total

    return [{"name": key, "count": value} for key, value in category_counts.items()]


def recent_by_intent(intent, limit=6):
    _ensure_schema()
    return search(listing_intent=intent, limit=limit, sort="newest")


def viewed_by_session(session_id, limit=6):
    _ensure_schema()
    rows = query_all(
        """SELECT p.* FROM properties p
           JOIN (
             SELECT property_id, MAX(viewed_at) AS last_view
             FROM property_views
             WHERE session_id=%s
             GROUP BY property_id
             ORDER BY last_view DESC
             LIMIT %s
           ) recent ON recent.property_id = p.id
           WHERE p.status='available'
           ORDER BY recent.last_view DESC""",
        (session_id, limit),
    )
    return [_parse(r) for r in rows]


def nearby_properties(lat, lng, radius_km=8, limit=8):
    _ensure_schema()
    rows = query_all(
        """SELECT * FROM properties
           WHERE status='available' AND latitude IS NOT NULL AND longitude IS NOT NULL"""
    )
    scored = []
    for row in rows:
        try:
            distance = _haversine_km(lat, lng, row["latitude"], row["longitude"])
        except Exception:
            continue
        if distance <= float(radius_km):
            parsed = _parse(row)
            parsed["distance_km"] = round(distance, 2)
            scored.append(parsed)
    scored.sort(key=lambda item: item.get("distance_km", 9999))
    return scored[:limit]
