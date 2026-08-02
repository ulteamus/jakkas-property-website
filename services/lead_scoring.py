"""Lead Scoring AI - scores 0-100, tiers cold/warm/hot."""
from pathlib import Path

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False


def _load_model():
    from config import LEAD_MODEL_PATH
    if HAS_JOBLIB and LEAD_MODEL_PATH.exists():
        return joblib.load(LEAD_MODEL_PATH)
    return None


def compute_lead_score(lead):
    """Rule-based + optional ML model."""
    score = 0
    score += min(lead.get("properties_viewed", 0) * 8, 24)
    score += min(lead.get("time_on_site_sec", 0) // 30, 15)
    score += min(lead.get("saved_count", 0) * 10, 20)
    score += min(lead.get("whatsapp_clicks", 0) * 12, 24)
    score += min(lead.get("call_clicks", 0) * 10, 20)
    if lead.get("property_id"):
        score += 10
    if lead.get("budget"):
        score += 7
    if lead.get("email"):
        score += 3

    model = _load_model()
    if model is not None:
        try:
            import numpy as np
            features = [[
                lead.get("properties_viewed", 0),
                lead.get("time_on_site_sec", 0),
                lead.get("saved_count", 0),
                lead.get("whatsapp_clicks", 0),
                lead.get("call_clicks", 0),
                1 if lead.get("property_id") else 0,
            ]]
            ml_score = float(model.predict(features)[0])
            score = int(0.5 * score + 0.5 * min(100, max(0, ml_score)))
        except Exception:
            pass

    score = min(100, max(0, score))
    if score >= 70:
        tier = "hot"
    elif score >= 40:
        tier = "warm"
    else:
        tier = "cold"
    return score, tier


def increment_lead_signal(mobile=None, lead_id=None, **kwargs):
    """Update lead engagement signals from events."""
    from database import execute, query_one
    if lead_id:
        lid = lead_id
    elif mobile:
        row = query_one("SELECT id FROM leads WHERE mobile=%s ORDER BY id DESC LIMIT 1", (mobile,))
        lid = row["id"] if row else None
    else:
        return

    if not lid:
        return
    sets = []
    params = []
    for field in ("whatsapp_clicks", "call_clicks", "properties_viewed", "saved_count", "time_on_site_sec"):
        if field in kwargs:
            sets.append(f"{field}={field}+%s")
            params.append(kwargs[field])
    if sets:
        params.append(lid)
        execute(f"UPDATE leads SET {', '.join(sets)} WHERE id=%s", params)
        from models.lead import refresh_score
        refresh_score(lid)
