from database import execute, query_all, query_one


def record_visitor(visitor_id, session_id, ip_hash=None, user_agent=None):
    existing = query_one("SELECT id, visit_count FROM visitors WHERE visitor_id=%s", (visitor_id,))
    if existing:
        execute(
            "UPDATE visitors SET last_visit=NOW(), visit_count=visit_count+1, session_id=%s WHERE visitor_id=%s",
            (session_id, visitor_id),
        )
    else:
        execute(
            "INSERT INTO visitors (visitor_id,session_id,ip_hash,user_agent) VALUES (%s,%s,%s,%s)",
            (visitor_id, session_id, ip_hash, user_agent),
        )


def record_event(visitor_id, event_type, property_id=None, meta=None):
    import json
    execute(
        "INSERT INTO visitor_events (visitor_id,event_type,property_id,meta) VALUES (%s,%s,%s,%s)",
        (visitor_id, event_type, property_id, json.dumps(meta) if meta else None),
    )


def record_property_view(property_id, visitor_id, session_id):
    execute(
        "INSERT INTO property_views (property_id,visitor_id,session_id) VALUES (%s,%s,%s)",
        (property_id, visitor_id, session_id),
    )
    from models import property as prop_model
    prop_model.increment_views(property_id)


def record_search(area=None, property_type=None, min_budget=None, max_budget=None, bhk=None, session_id=None):
    execute(
        """INSERT INTO search_analytics (area_name,property_type,min_budget,max_budget,bhk,session_id)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (area, property_type, min_budget, max_budget, bhk, session_id),
    )
    if area:
        execute(
            """INSERT INTO area_demand (area_name, search_count) VALUES (%s,1)
               ON DUPLICATE KEY UPDATE search_count=search_count+1""",
            (area,),
        )


def dashboard_stats():
    props = query_one(
        """SELECT COUNT(*) AS total,
                  SUM(CASE WHEN status='available' THEN 1 ELSE 0 END) AS available,
                  SUM(CASE WHEN status='sold' THEN 1 ELSE 0 END) AS sold
           FROM properties"""
    )
    visitors = query_one("SELECT COUNT(*) AS total FROM visitors")
    returning = query_one("SELECT COUNT(*) AS c FROM visitors WHERE visit_count>1")
    views = query_one("SELECT COUNT(*) AS c FROM property_views")
    inquiries = query_one("SELECT COUNT(*) AS c FROM inquiries")
    return {
        "total_properties": props["total"] or 0,
        "available_properties": props["available"] or 0,
        "sold_properties": props["sold"] or 0,
        "total_visitors": visitors["total"] or 0,
        "returning_visitors": returning["c"] or 0,
        "property_views": views["c"] or 0,
        "total_inquiries": inquiries["c"] or 0,
    }


def trending_areas(limit=8):
    return query_all(
        "SELECT * FROM area_demand ORDER BY demand_score DESC, search_count DESC LIMIT %s",
        (limit,),
    )


def most_viewed_properties(limit=10):
    return query_all(
        """SELECT id, property_name, area_name, price, view_count, primary_image, slug
           FROM properties ORDER BY view_count DESC LIMIT %s""",
        (limit,),
    )


def demand_by_type():
    return query_all(
        """SELECT property_type, COUNT(*) AS cnt, AVG(price) AS avg_price
           FROM properties WHERE status='available' GROUP BY property_type"""
    )


def budget_distribution():
    return query_all(
        """SELECT
             CASE
               WHEN price < 3000000 THEN 'Under 30L'
               WHEN price < 5000000 THEN '30L - 50L'
               WHEN price < 10000000 THEN '50L - 1Cr'
               WHEN price < 20000000 THEN '1Cr - 2Cr'
               ELSE 'Above 2Cr'
             END AS budget_range,
             COUNT(*) AS cnt
           FROM search_analytics WHERE max_budget IS NOT NULL
           GROUP BY budget_range"""
    )


def conversion_rate():
    visitors = query_one("SELECT COUNT(*) AS c FROM visitors")["c"] or 1
    leads = query_one("SELECT COUNT(*) AS c FROM leads")["c"] or 0
    return round((leads / visitors) * 100, 2) if visitors else 0


def update_area_demand_from_views():
    execute(
        """INSERT INTO area_demand (area_name, view_count, demand_score)
           SELECT area_name, COUNT(*), COUNT(*) * 1.5 FROM property_views pv
           JOIN properties p ON p.id=pv.property_id
           WHERE pv.viewed_at > NOW() - INTERVAL 30 DAY
           GROUP BY area_name
           ON DUPLICATE KEY UPDATE view_count=VALUES(view_count),
           demand_score=VALUES(demand_score)"""
    )
