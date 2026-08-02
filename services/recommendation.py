from models import property as prop_model


def recommend_for_property(property_id, limit=4):
    return prop_model.similar(property_id, limit)


def recommend_for_user(area=None, budget=None, bhk=None, property_type=None, listing_intent=None, limit=6):
    max_p = float(budget) * 1.15 if budget else None
    min_p = float(budget) * 0.7 if budget else None
    results = prop_model.search(
        area=area, property_type=property_type, min_price=min_p,
        max_price=max_p, bhk=bhk, listing_intent=listing_intent, limit=limit * 2,
    )
    if not results:
        results = prop_model.featured(limit)
    return results[:limit]
