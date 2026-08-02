import re
import uuid
from collections import Counter

from flask import Blueprint, jsonify, request, session

from database import execute, query_all
from models import property as prop_model
from models import lead as lead_model
from models import inquiry as inquiry_model
from models import analytics as analytics_model
from models import reviews as reviews_model
from services import recommendation, price_prediction, whatsapp as wa_service
from services import india_property_predictor
from services.lead_scoring import increment_lead_signal
from utils.helpers import format_inr
from config import COMPANY_NAME, COMPANY_PHONE, COMPANY_WHATSAPP

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _serialize_property(p, media=None, public=True):
    if not p:
        return None
    p = prop_model.to_dict(p, public=public)
    images = []
    videos = []
    if media:
        images = [
            {"file_path": i["file_path"], "is_primary": bool(i.get("is_primary"))}
            for i in media.get("images", [])
        ]
        videos = [
            {"file_path": v["file_path"], "title": v.get("title")}
            for v in media.get("videos", [])
        ]
    return {
        "id": p["id"], "property_name": p["property_name"], "slug": p.get("slug"),
        "property_type": p["property_type"], "area_name": p["area_name"],
        "price": float(p["price"]), "bhk": p["bhk"], "sq_ft": float(p["sq_ft"]),
        "description": p.get("description"), "amenities": p.get("amenities") or [],
        "latitude": float(p["latitude"]) if p.get("latitude") is not None else None,
        "longitude": float(p["longitude"]) if p.get("longitude") is not None else None,
        "status": p["status"], "is_featured": bool(p.get("is_featured")),
        "primary_image": p.get("primary_image"), "view_count": p.get("view_count", 0),
        "listing_type": p.get("listing_type"),
        "listing_intent": p.get("listing_intent", "buy"),
        "display_type": p.get("display_type"),
        "address": p.get("address"),
        "images": images,
        "videos": videos,
    }


def _serialize_properties(props, public=True):
    media_map = prop_model.get_media_bulk([p["id"] for p in props])
    return [_serialize_property(p, media_map.get(p["id"]), public=public) for p in props]


def _extract_budget(query):
    q = (query or "").lower().replace(",", "")
    under_lakh = re.search(r"under\s+(\d+(?:\.\d+)?)\s*lakh", q)
    if under_lakh:
        return 0, float(under_lakh.group(1)) * 100000
    around_lakh = re.search(r"around\s+(\d+(?:\.\d+)?)\s*lakh", q)
    if around_lakh:
        base = float(around_lakh.group(1)) * 100000
        return base * 0.8, base * 1.2
    under_crore = re.search(r"under\s+(\d+(?:\.\d+)?)\s*crore", q)
    if under_crore:
        return 0, float(under_crore.group(1)) * 10000000
    around_crore = re.search(r"around\s+(\d+(?:\.\d+)?)\s*crore", q)
    if around_crore:
        base = float(around_crore.group(1)) * 10000000
        return base * 0.8, base * 1.2
    under_number = re.search(r"under\s+(\d{5,})", q)
    if under_number:
        return 0, float(under_number.group(1))
    return None, None


def _extract_bhk(query):
    match = re.search(r"(\d)\s*bhk", (query or "").lower())
    return int(match.group(1)) if match else None


def _extract_intent(query):
    q = (query or "").lower()
    if "rent" in q or "rental" in q:
        return "rent"
    if "sell" in q or "sale" in q:
        return "sell"
    if "buy" in q:
        return "buy"
    return None


def _extract_property_type(query):
    q = (query or "").lower()
    keywords = [
        "apartment",
        "flat",
        "villa",
        "bungalow",
        "plot",
        "commercial",
        "residential",
        "shop",
        "office",
    ]
    for word in keywords:
        if word in q:
            return word
    return None


def _extract_location(query):
    q = (query or "").lower()
    areas = [
        "vesu",
        "adajan",
        "ring road",
        "piplod",
        "pal",
        "city light",
        "althan",
        "katargam",
        "varachha",
        "dumas",
        "surat",
    ]
    for area in areas:
        if area in q:
            return area.title()
    return None


def _parse_smart_query(query):
    min_budget, max_budget = _extract_budget(query)
    return {
        "query": query,
        "bhk": _extract_bhk(query),
        "listing_intent": _extract_intent(query),
        "property_type": _extract_property_type(query),
        "location": _extract_location(query),
        "min_price": min_budget,
        "max_price": max_budget,
    }


def _infer_preferences(history):
    if not history:
        return {}
    area_counter = Counter(p.get("area_name") for p in history if p.get("area_name"))
    type_counter = Counter(p.get("property_type") for p in history if p.get("property_type"))
    intent_counter = Counter(p.get("listing_intent") for p in history if p.get("listing_intent"))
    bhk_values = [int(p.get("bhk")) for p in history if p.get("bhk")]
    budget_values = [float(p.get("price")) for p in history if p.get("price")]
    return {
        "area_name": area_counter.most_common(1)[0][0] if area_counter else None,
        "property_type": type_counter.most_common(1)[0][0] if type_counter else None,
        "listing_intent": intent_counter.most_common(1)[0][0] if intent_counter else None,
        "bhk": round(sum(bhk_values) / len(bhk_values)) if bhk_values else None,
        "budget": round(sum(budget_values) / len(budget_values)) if budget_values else None,
    }


def _match_percentage(prop, prefs):
    score = 45
    if prefs.get("area_name") and prop.get("area_name") == prefs["area_name"]:
        score += 20
    if prefs.get("property_type") and prop.get("property_type") == prefs["property_type"]:
        score += 15
    if prefs.get("listing_intent") and prop.get("listing_intent") == prefs["listing_intent"]:
        score += 10
    if prefs.get("bhk") and prop.get("bhk") and abs(int(prop["bhk"]) - int(prefs["bhk"])) <= 1:
        score += 10
    if prefs.get("budget") and prop.get("price"):
        lower = float(prefs["budget"]) * 0.75
        upper = float(prefs["budget"]) * 1.25
        if lower <= float(prop["price"]) <= upper:
            score += 12
    return max(52, min(98, int(score)))


def _format_property_line(prop):
    bhk = f"{prop['bhk']} BHK · " if prop.get("bhk") else ""
    rent_suffix = "/mo" if prop.get("listing_type") == "rent" else ""
    area = prop.get("area_name") or "Surat"
    return f"• {prop['property_name']} — {area}, {bhk}{format_inr(prop['price'])}{rent_suffix}"


def _describe_search_criteria(parsed):
    parts = []
    if parsed.get("bhk"):
        parts.append(f"{parsed['bhk']} BHK")
    if parsed.get("property_type"):
        parts.append(parsed["property_type"].title())
    if parsed.get("location"):
        parts.append(f"in {parsed['location']}")
    if parsed.get("max_price"):
        parts.append(f"under {format_inr(parsed['max_price'])}")
    elif parsed.get("min_price"):
        parts.append(f"from {format_inr(parsed['min_price'])}")
    if parsed.get("listing_intent"):
        parts.append(f"for {parsed['listing_intent']}")
    return ", ".join(parts) if parts else "your requirements"


def _find_similar_properties(parsed, limit=4):
    similar = []
    if parsed.get("max_price") or parsed.get("min_price"):
        similar = prop_model.search(
            property_type=parsed.get("property_type"),
            area=parsed.get("location"),
            listing_intent=parsed.get("listing_intent"),
            bhk=parsed.get("bhk"),
            limit=limit,
        )
    if not similar and parsed.get("location"):
        similar = prop_model.search(
            area=parsed.get("location"),
            listing_intent=parsed.get("listing_intent"),
            limit=limit,
        )
    if not similar and parsed.get("property_type"):
        similar = prop_model.search(
            property_type=parsed.get("property_type"),
            listing_intent=parsed.get("listing_intent"),
            limit=limit,
        )
    if not similar and parsed.get("bhk"):
        similar = prop_model.search(bhk=parsed.get("bhk"), limit=limit)
    if not similar:
        similar = prop_model.search(limit=limit, sort="views")
    return similar


def _build_chat_reply(message, parsed, properties):
    q_lower = message.lower()
    whatsapp_number = str(COMPANY_WHATSAPP).lstrip("+")
    criteria = _describe_search_criteria(parsed)

    if any(token in q_lower for token in ["hello", "hi", "hey", "good morning", "good evening", "namaste"]):
        return (
            "Good day, and welcome to Jakkash Property Consultancy.\n\n"
            "I'm here to help you discover residential and commercial properties across Surat — "
            "whether you're buying, selling, or renting.\n\n"
            "Share your preference (area, budget, or property type), and I'll shortlist suitable options for you."
        )

    if any(token in q_lower for token in ["contact", "phone", "broker", "whatsapp"]):
        return (
            f"Certainly. You may reach {COMPANY_NAME} directly:\n"
            f"• Phone: {COMPANY_PHONE}\n"
            f"• WhatsApp: +{whatsapp_number}\n\n"
            "Our property advisors are available to guide you through viewings, documentation, and negotiations."
        )

    if re.search(r"\bcall\b", q_lower):
        return (
            f"Certainly. You may reach {COMPANY_NAME} directly:\n"
            f"• Phone: {COMPANY_PHONE}\n"
            f"• WhatsApp: +{whatsapp_number}\n\n"
            "Our property advisors are available to guide you through viewings, documentation, and negotiations."
        )

    if any(token in q_lower for token in ["visit", "appointment", "site tour", "viewing"]):
        return (
            "Site visits can be arranged in a few simple steps:\n"
            "• Browse our listings and open a property you like\n"
            "• Use the schedule visit option on the property page\n"
            "• Share your name, mobile number, and preferred date\n\n"
            "Our team will confirm your appointment shortly. You may also message us on WhatsApp for a quicker response."
        )

    if properties:
        count = len(properties)
        noun = "option" if count == 1 else "options"
        lines = [
            f"Thank you for your enquiry. Based on {criteria}, I've shortlisted {count} suitable {noun}:",
            "",
        ]
        for prop in properties[:5]:
            lines.append(_format_property_line(prop))
        if count > 5:
            lines.append(f"\n…and {count - 5} more matching listings shown below.")
        lines.append("\nOpen any listing for full details, photos, or to request a site visit.")
        return "\n".join(lines)

    if any(
        token in q_lower
        for token in ["availability", "available", "property", "rent", "buy", "sell", "bhk", "flat", "villa", "plot", "commercial"]
    ):
        similar = _find_similar_properties(parsed)
        if similar:
            lines = [
                f"I couldn't find an exact match for {criteria} at the moment.",
                "Here are some closely related options you may wish to consider:",
                "",
            ]
            for prop in similar[:4]:
                lines.append(_format_property_line(prop))
            lines.append(
                "\nYou might also try adjusting your budget or exploring a nearby locality. "
                "Our team is happy to assist on WhatsApp or call."
            )
            return {"reply": "\n".join(lines), "properties": similar}

        return (
            f"I couldn't locate listings matching {criteria} right now.\n\n"
            "You may try a nearby area (e.g. Vesu, Adajan, Piplod), broaden your budget, "
            "or browse all properties on our listings page. Our advisors can also suggest off-market options — "
            f"reach us at {COMPANY_PHONE}."
        )

    return (
        "I'm your property assistant at Jakkash Property Consultancy, Surat.\n\n"
        "You can ask me about:\n"
        "• Available properties (e.g. \"2 BHK under 60 lakh in Vesu\")\n"
        "• Commercial or rental options\n"
        "• Booking a site visit\n"
        "• Speaking with our advisory team\n\n"
        "How may I assist you today?"
    )


@api_bp.route("/properties")
def api_properties():
    keyword = (request.args.get("q") or "").strip()
    property_id = request.args.get("property_id", type=int)
    if property_id is not None and property_id <= 0:
        property_id = None
    if property_id is None and keyword.isdigit():
        property_id = int(keyword)
        keyword = ""

    listing_intent = (request.args.get("listing_intent") or "").strip().lower()
    if listing_intent == "sell":
        listing_intent = "buy"

    limit = request.args.get("limit", type=int) or 100
    limit = min(limit, 120)
    props = prop_model.search(
        area=request.args.get("area"),
        location=request.args.get("location"),
        city=request.args.get("city"),
        property_type=request.args.get("type"),
        min_price=request.args.get("min_price", type=float),
        max_price=request.args.get("max_price", type=float),
        min_sq_ft=request.args.get("min_sq_ft", type=float),
        max_sq_ft=request.args.get("max_sq_ft", type=float),
        bhk=request.args.get("bhk", type=int),
        status=request.args.get("status", "available"),
        property_id=property_id,
        keyword=keyword,
        listing_intent=listing_intent or None,
        sort=request.args.get("sort", "newest"),
        limit=limit,
    )
    try:
        analytics_model.record_search(
            area=request.args.get("area"), property_type=request.args.get("type"),
            min_budget=request.args.get("min_price", type=float),
            max_budget=request.args.get("max_price", type=float),
            bhk=request.args.get("bhk", type=int), session_id=session.get("session_id"),
        )
    except Exception:
        pass
    return jsonify({"success": True, "properties": _serialize_properties(props)})


@api_bp.route("/properties/map")
def api_map():
    markers = prop_model.map_markers()
    for m in markers:
        m["price_fmt"] = format_inr(m["price"])
    return jsonify({"success": True, "markers": markers})


@api_bp.route("/properties/<int:pid>/similar")
def api_similar(pid):
    return jsonify({"success": True, "properties": _serialize_properties(prop_model.similar(pid))})


@api_bp.route("/properties/nearby")
def api_properties_nearby():
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    if lat is None or lng is None:
        return jsonify({"success": False, "error": "Latitude and longitude are required"}), 400
    radius_km = request.args.get("radius_km", default=10.0, type=float)
    limit = min(request.args.get("limit", default=8, type=int), 20)
    rows = prop_model.nearby_properties(lat, lng, radius_km=radius_km, limit=limit)
    media_map = prop_model.get_media_bulk([row["id"] for row in rows])
    serialized = []
    for row in rows:
        item = _serialize_property(row, media_map.get(row["id"]))
        item["distance_km"] = row.get("distance_km")
        serialized.append(item)
    return jsonify({"success": True, "properties": serialized})


@api_bp.route("/properties/suggest")
def api_property_suggest():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"success": True, "properties": []})
    props = prop_model.search(keyword=query, limit=6, sort="views")
    return jsonify({"success": True, "properties": _serialize_properties(props)})


@api_bp.route("/properties/smart-search", methods=["POST"])
def api_smart_search():
    data = request.get_json() or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"success": False, "error": "Query required"}), 400

    parsed = _parse_smart_query(query)
    try:
        limit = min(int(data.get("limit", 12)), 24)
    except (TypeError, ValueError):
        limit = 12
    has_structured_filters = any(
        [
            parsed["property_type"],
            parsed["location"],
            parsed["listing_intent"],
            parsed["min_price"],
            parsed["max_price"],
            parsed["bhk"],
        ]
    )
    props = prop_model.search(
        keyword=None if has_structured_filters else query,
        property_type=parsed["property_type"],
        area=parsed["location"],
        listing_intent=parsed["listing_intent"],
        min_price=parsed["min_price"],
        max_price=parsed["max_price"],
        bhk=parsed["bhk"],
        limit=limit,
    )
    return jsonify(
        {
            "success": True,
            "parsed": parsed,
            "properties": _serialize_properties(props),
        }
    )


@api_bp.route("/inquiry", methods=["POST"])
def api_inquiry():
    data = request.get_json() or request.form
    required = ["name", "mobile"]
    if not all(data.get(k) for k in required):
        return jsonify({"success": False, "error": "Name and mobile required"}), 400
    iid = inquiry_model.create(data)
    lead_model.create_from_inquiry(data, inquiry_id=iid)
    return jsonify({"success": True, "message": "Inquiry submitted. We will contact you soon."})


@api_bp.route("/reviews", methods=["POST"])
def api_create_review():
    data = request.get_json() or request.form
    name = (data.get("name") or "").strip()
    review_text = (data.get("review_text") or data.get("message") or "").strip()
    location = (data.get("location") or "Surat").strip()
    rating = data.get("rating", 5)
    if not name or not review_text:
        return jsonify({"success": False, "error": "Name and review text are required"}), 400
    try:
        reviews_model.create_review(name, location, review_text, rating=rating, is_active=True)
    except Exception:
        return jsonify({"success": False, "error": "Unable to save review"}), 500
    return jsonify({"success": True, "message": "Thanks! Your review has been posted."})


@api_bp.route("/reviews/<int:review_id>/comments", methods=["POST"])
def api_create_review_comment(review_id):
    data = request.get_json() or request.form
    commenter_name = (data.get("name") or data.get("commenter_name") or "").strip()
    comment_text = (data.get("comment_text") or "").strip()
    commenter_email = (data.get("email") or "").strip()
    if not commenter_name or not comment_text:
        return jsonify({"success": False, "error": "Name and comment are required"}), 400
    review = reviews_model.get_review(review_id)
    if not review:
        return jsonify({"success": False, "error": "Review not found"}), 404
    try:
        reviews_model.create_comment(
            review_id=review_id,
            commenter_name=commenter_name,
            comment_text=comment_text,
            commenter_email=commenter_email,
            is_active=True,
        )
    except Exception:
        return jsonify({"success": False, "error": "Unable to save comment"}), 500
    return jsonify({"success": True, "message": "Comment added."})


@api_bp.route("/visit-request", methods=["POST"])
def api_visit_request():
    data = request.get_json() or request.form
    required = ["name", "mobile", "property_id"]
    if not all(data.get(k) for k in required):
        return jsonify({"success": False, "error": "Name, mobile and property are required"}), 400

    site_visit_message = (
        f"Site visit request for property #{data.get('property_id')}. "
        f"Preferred date: {data.get('preferred_date') or 'Not specified'}. "
        f"Notes: {data.get('message') or 'No notes'}"
    )
    payload = {
        "name": data.get("name"),
        "mobile": data.get("mobile"),
        "email": data.get("email"),
        "property_id": data.get("property_id"),
        "message": site_visit_message,
        "source": "site_visit_request",
    }
    iid = inquiry_model.create(payload)
    lead_model.create_from_inquiry(payload, inquiry_id=iid)
    return jsonify({"success": True, "message": "Site visit request submitted."})


@api_bp.route("/whatsapp/interest", methods=["POST"])
def api_whatsapp_interest():
    data = request.get_json() or {}
    pid = data.get("property_id")
    prop = prop_model.get_by_id(pid) if pid else None
    increment_lead_signal(mobile=data.get("mobile"), whatsapp_clicks=1)
    if session.get("visitor_id"):
        analytics_model.record_event(session["visitor_id"], "whatsapp_click", pid)
    if prop:
        url = wa_service.interest_message(
            prop["property_name"], prop["area_name"], prop["price"],
            data.get("name", ""), data.get("mobile", ""),
        )
    else:
        url = wa_service.general_inquiry(data.get("name", "Customer"), data.get("mobile", ""))
    return jsonify({"success": True, "whatsapp_url": url})


@api_bp.route("/event/call", methods=["POST"])
def api_call_click():
    data = request.get_json() or {}
    increment_lead_signal(mobile=data.get("mobile"), call_clicks=1)
    if session.get("visitor_id"):
        analytics_model.record_event(session["visitor_id"], "call_click", data.get("property_id"))
    return jsonify({"success": True})


@api_bp.route("/saved", methods=["GET", "POST", "DELETE"])
def api_saved():
    sid = session.get("session_id")
    if not sid:
        session["session_id"] = str(uuid.uuid4())
        sid = session["session_id"]

    if request.method == "GET":
        rows = query_all(
            """SELECT p.* FROM saved_properties sp JOIN properties p ON p.id=sp.property_id
               WHERE sp.session_id=%s""", (sid,)
        )
        props = [prop_model.get_by_id(r["id"]) for r in rows]
        props = [p for p in props if p]
        return jsonify({"success": True, "properties": _serialize_properties(props)})

    data = request.get_json() or {}
    pid = data.get("property_id")
    if request.method == "POST" and pid:
        try:
            execute(
                "INSERT IGNORE INTO saved_properties (session_id,property_id) VALUES (%s,%s)",
                (sid, pid),
            )
            increment_lead_signal(saved_count=1)
            analytics_model.record_event(session.get("visitor_id"), "save_property", pid)
        except Exception:
            pass
        return jsonify({"success": True})
    if request.method == "DELETE" and pid:
        execute("DELETE FROM saved_properties WHERE session_id=%s AND property_id=%s", (sid, pid))
        return jsonify({"success": True})
    return jsonify({"success": False}), 400


@api_bp.route("/recommendations")
def api_recommendations():
    sid = session.get("session_id")
    viewed = prop_model.viewed_by_session(sid, 8) if sid else []
    saved = []
    if sid:
        rows = query_all(
            """SELECT p.id FROM saved_properties sp
               JOIN properties p ON p.id=sp.property_id
               WHERE sp.session_id=%s
               ORDER BY sp.created_at DESC LIMIT 8""",
            (sid,),
        )
        saved = [prop_model.get_by_id(row["id"]) for row in rows]
        saved = [p for p in saved if p]

    history = viewed + saved
    prefs = _infer_preferences(history)
    recommended_rows = recommendation.recommend_for_user(
        area=prefs.get("area_name"),
        budget=prefs.get("budget"),
        bhk=prefs.get("bhk"),
        property_type=prefs.get("property_type"),
        listing_intent=prefs.get("listing_intent"),
        limit=10,
    )
    recommended = []
    media_map = prop_model.get_media_bulk([row["id"] for row in recommended_rows])
    for row in recommended_rows:
        serialized = _serialize_property(row, media_map.get(row["id"]))
        serialized["match_percentage"] = _match_percentage(row, prefs)
        recommended.append(serialized)

    similar_rows = prop_model.similar(history[0]["id"], limit=6) if history else []
    trending_ids = analytics_model.most_viewed_properties(6)
    trending_rows = [prop_model.get_by_id(item["id"]) for item in trending_ids]
    trending_rows = [p for p in trending_rows if p]

    return jsonify(
        {
            "success": True,
            "recommended": recommended,
            "similar": _serialize_properties(similar_rows),
            "recently_viewed": _serialize_properties(viewed),
            "trending": _serialize_properties(trending_rows),
        }
    )


@api_bp.route("/predict-price", methods=["POST"])
def api_predict():
    data = request.get_json() or {}
    locality = (data.get("area_name") or data.get("locality") or data.get("location_area") or "").strip()
    city = (data.get("city") or "Surat").strip()
    try:
        if locality:
            result = india_property_predictor.predict_price(
                city=city,
                locality=locality,
                area_sqft=data.get("sq_ft") or data.get("area_sq_ft") or 1000,
                bhk=data.get("bhk", 0),
                property_type=data.get("property_type", "apartment"),
            )
        else:
            result = price_prediction.predict(
                data.get("area_name", "Surat"),
                data.get("bhk", 0),
                data.get("sq_ft", 1000),
                data.get("property_type", "flat"),
            )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        return jsonify({"success": False, "error": "Unable to predict price right now."}), 500
    return jsonify({"success": True, **result})


@api_bp.route("/analytics/trending")
def api_trending():
    return jsonify({
        "success": True,
        "areas": analytics_model.trending_areas(),
        "by_type": analytics_model.demand_by_type(),
    })


@api_bp.route("/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "Message required"}), 400

    parsed = _parse_smart_query(message)
    q_lower = message.lower()
    properties = []

    if any(
        token in q_lower
        for token in ["bhk", "property", "rent", "buy", "sell", "flat", "villa", "plot", "commercial", "bungalow", "office", "apartment"]
    ):
        has_structured_filters = any(
            [
                parsed.get("property_type"),
                parsed.get("location"),
                parsed.get("listing_intent"),
                parsed.get("min_price"),
                parsed.get("max_price"),
                parsed.get("bhk"),
            ]
        )
        properties = prop_model.search(
            keyword=None if has_structured_filters else parsed.get("query"),
            property_type=parsed.get("property_type"),
            area=parsed.get("location"),
            listing_intent=parsed.get("listing_intent"),
            min_price=parsed.get("min_price"),
            max_price=parsed.get("max_price"),
            bhk=parsed.get("bhk"),
            limit=6,
        )

    reply_result = _build_chat_reply(message, parsed, properties)
    if isinstance(reply_result, dict):
        reply = reply_result["reply"]
        properties = reply_result.get("properties", properties)
    else:
        reply = reply_result

    try:
        analytics_model.record_event(
            session.get("visitor_id"),
            "search",
            meta={"query": message, "intent": parsed.get("listing_intent")},
        )
    except Exception:
        pass

    return jsonify(
        {
            "success": True,
            "reply": reply,
            "properties": _serialize_properties(properties),
            "parsed": parsed,
        }
    )
