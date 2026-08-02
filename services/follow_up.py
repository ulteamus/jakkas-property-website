from models import lead as lead_model


def check_follow_ups():
    lead_model.mark_urgent_stale()
    return lead_model.get_all(urgent_only=True, limit=50)
