import json
from database import execute, query_all, query_one


def _parse_row(row):
    if row and row.get("amenities") and isinstance(row["amenities"], str):
        try:
            row["amenities"] = json.loads(row["amenities"])
        except json.JSONDecodeError:
            row["amenities"] = []
    return row


def get_by_id(property_id):
    row = query_one("SELECT * FROM properties WHERE id = %s", (property_id,))
    return _parse_row(row)


def search(city=None, property_type=None, min_price=None, max_price=None,
           min_bedrooms=None, listing_type=None, keyword=None, limit=50):
    sql = "SELECT * FROM properties WHERE status = 'available'"
    params = []

    if city:
        sql += " AND city LIKE %s"
        params.append(f"%{city}%")
    if property_type:
        sql += " AND property_type = %s"
        params.append(property_type)
    if listing_type:
        sql += " AND listing_type = %s"
        params.append(listing_type)
    if min_price is not None:
        sql += " AND price >= %s"
        params.append(min_price)
    if max_price is not None:
        sql += " AND price <= %s"
        params.append(max_price)
    if min_bedrooms is not None:
        sql += " AND bedrooms >= %s"
        params.append(min_bedrooms)
    if keyword:
        sql += " AND (title LIKE %s OR description LIKE %s OR locality LIKE %s)"
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])

    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    return [_parse_row(r) for r in query_all(sql, params)]


def get_all(limit=200):
    rows = query_all(
        "SELECT * FROM properties ORDER BY created_at DESC LIMIT %s", (limit,)
    )
    return [_parse_row(r) for r in rows]


def create(data, created_by=None):
    amenities = json.dumps(data.get("amenities") or [])
    pid = execute(
        """INSERT INTO properties
           (title, description, property_type, listing_type, city, locality, address,
            bedrooms, bathrooms, area_sqft, price, year_built, amenities, image_url, created_by)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            data["title"], data.get("description"), data["property_type"],
            data.get("listing_type", "sale"), data["city"], data.get("locality"),
            data.get("address"), data.get("bedrooms", 0), data.get("bathrooms", 0),
            data["area_sqft"], data["price"], data.get("year_built"),
            amenities, data.get("image_url"), created_by,
        ),
    )
    return get_by_id(pid)


def update(property_id, data):
    amenities = json.dumps(data.get("amenities") or [])
    execute(
        """UPDATE properties SET title=%s, description=%s, property_type=%s, listing_type=%s,
           city=%s, locality=%s, address=%s, bedrooms=%s, bathrooms=%s, area_sqft=%s,
           price=%s, year_built=%s, amenities=%s, status=%s WHERE id=%s""",
        (
            data["title"], data.get("description"), data["property_type"],
            data.get("listing_type", "sale"), data["city"], data.get("locality"),
            data.get("address"), data.get("bedrooms", 0), data.get("bathrooms", 0),
            data["area_sqft"], data["price"], data.get("year_built"),
            amenities, data.get("status", "available"), property_id,
        ),
    )


def delete(property_id):
    execute("DELETE FROM properties WHERE id = %s", (property_id,))


def add_image(property_id, image_path, is_primary=False):
    if is_primary:
        execute(
            "UPDATE property_images SET is_primary = 0 WHERE property_id = %s",
            (property_id,),
        )
    execute(
        "INSERT INTO property_images (property_id, image_path, is_primary) VALUES (%s, %s, %s)",
        (property_id, image_path, 1 if is_primary else 0),
    )


def get_images(property_id):
    return query_all(
        "SELECT * FROM property_images WHERE property_id = %s ORDER BY is_primary DESC",
        (property_id,),
    )


def compare(property_ids):
    if not property_ids:
        return []
    placeholders = ",".join(["%s"] * len(property_ids))
    rows = query_all(
        f"SELECT * FROM properties WHERE id IN ({placeholders})", tuple(property_ids)
    )
    return [_parse_row(r) for r in rows]
