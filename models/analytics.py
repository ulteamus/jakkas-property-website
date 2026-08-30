from database import execute, query_all, query_one


def record_visitor(visitor_id, session_id, ip_hash=None, user_agent=None):
    # Single round-trip upsert (Postgres + SQLite). Fallback to select/update on failure.
    try:
        from database.db import use_postgres, use_sqlite

        if use_postgres():
            execute(
                """INSERT INTO visitors (visitor_id,session_id,ip_hash,user_agent,visit_count,last_visit)
                   VALUES (%s,%s,%s,%s,1,NOW())
                   ON CONFLICT (visitor_id) DO UPDATE SET
                     last_visit=NOW(),
                     visit_count=visitors.visit_count+1,
                     session_id=EXCLUDED.session_id""",
                (visitor_id, session_id, ip_hash, user_agent),
            )
            return
        if use_sqlite():
            execute(
                """INSERT INTO visitors (visitor_id,session_id,ip_hash,user_agent,visit_count,last_visit)
                   VALUES (%s,%s,%s,%s,1,CURRENT_TIMESTAMP)
                   ON CONFLICT(visitor_id) DO UPDATE SET
                     last_visit=CURRENT_TIMESTAMP,
                     visit_count=visit_count+1,
                     session_id=excluded.session_id""",
                (visitor_id, session_id, ip_hash, user_agent),
            )
            return
    except Exception:
        pass
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
    """Single round-trip aggregation for admin/home KPI cards."""
    row = query_one(
        """SELECT
             (SELECT COUNT(*) FROM properties) AS total_properties,
             (SELECT COUNT(*) FROM properties WHERE status='available') AS available_properties,
             (SELECT COUNT(*) FROM properties WHERE status='sold') AS sold_properties,
             (SELECT COUNT(*) FROM visitors) AS total_visitors,
             (SELECT COUNT(*) FROM visitors WHERE visit_count>1) AS returning_visitors,
             (SELECT COUNT(*) FROM property_views) AS property_views,
             (SELECT COUNT(*) FROM inquiries) AS total_inquiries,
             (SELECT COUNT(*) FROM leads) AS lead_total,
             (SELECT COUNT(*) FROM leads WHERE status='new') AS lead_new,
             (SELECT COUNT(*) FROM leads WHERE lead_tier='hot') AS lead_hot,
             (SELECT COUNT(*) FROM leads WHERE is_urgent=1) AS lead_urgent
        """
    ) or {}
    total_visitors = int(row.get("total_visitors") or 0)
    lead_total = int(row.get("lead_total") or 0)
    return {
        "total_properties": int(row.get("total_properties") or 0),
        "available_properties": int(row.get("available_properties") or 0),
        "sold_properties": int(row.get("sold_properties") or 0),
        "total_visitors": total_visitors,
        "returning_visitors": int(row.get("returning_visitors") or 0),
        "property_views": int(row.get("property_views") or 0),
        "total_inquiries": int(row.get("total_inquiries") or 0),
        "total": lead_total,
        "new": int(row.get("lead_new") or 0),
        "hot": int(row.get("lead_hot") or 0),
        "urgent": int(row.get("lead_urgent") or 0),
        "conversion_rate": round((lead_total / total_visitors) * 100, 2) if total_visitors else 0,
    }


def home_property_count():
    """Lightweight count for the public homepage (avoids full dashboard_stats)."""
    row = query_one("SELECT COUNT(*) AS c FROM properties WHERE status='available'")
    return int((row or {}).get("c") or 0)


def home_kpi_counts():
    """One round-trip for homepage KPI strip."""
    row = query_one(
        """SELECT
             (SELECT COUNT(*) FROM properties WHERE status='available') AS properties,
             (SELECT COUNT(*) FROM inquiries) AS clients
        """
    ) or {}
    return {
        "properties": int(row.get("properties") or 0),
        "clients": int(row.get("clients") or 0),
        "years": 10,
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
    row = query_one(
        """SELECT
             (SELECT COUNT(*) FROM visitors) AS visitors,
             (SELECT COUNT(*) FROM leads) AS leads
        """
    ) or {}
    visitors = int(row.get("visitors") or 0) or 1
    leads = int(row.get("leads") or 0)
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
