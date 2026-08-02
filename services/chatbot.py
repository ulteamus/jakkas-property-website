import re
import uuid
from database import execute
from models import property_model
from services import emi_calculator, price_predictor, recommendation


INTENTS = [
    (r"\b(search|find|show|list)\b.*\b(propert|house|flat|apartment|villa)\b", "search"),
    (r"\b(recommend|suggestion|suggest)\b", "recommend"),
    (r"\b(predict|estimate|price)\b", "predict"),
    (r"\b(emi|loan|mortgage)\b", "emi"),
    (r"\b(compare|comparison|vs)\b", "compare"),
    (r"\b(visit|schedule|book)\b.*\b(site|visit|tour)\b", "visit"),
    (r"\b(hello|hi|hey|help)\b", "greeting"),
]


def detect_intent(message):
    msg = message.lower()
    for pattern, intent in INTENTS:
        if re.search(pattern, msg):
            return intent
    return "general"


def _extract_city(message):
    cities = ["mumbai", "delhi", "bangalore", "hyderabad", "chennai", "pune", "kolkata"]
    msg = message.lower()
    for c in cities:
        if c in msg:
            return c.title()
    return None


def _extract_numbers(message):
    nums = re.findall(r"[\d,.]+", message.replace(",", ""))
    return [float(n) for n in nums if n]


def generate_reply(message, user_id=None, session_id=None):
    intent = detect_intent(message)
    city = _extract_city(message)

    if intent == "greeting":
        reply = (
            "Hello! I'm your Property Broker AI assistant. I can help you:\n"
            "• Search properties (e.g. 'Find 2BHK in Bangalore')\n"
            "• Get recommendations\n"
            "• Predict property prices\n"
            "• Calculate EMI\n"
            "• Compare properties\n"
            "• Schedule site visits\n\n"
            "What would you like to do?"
        )
    elif intent == "search":
        props = property_model.search(city=city, limit=5)
        if props:
            lines = [f"Found {len(props)} properties" + (f" in {city}" if city else "") + ":"]
            for p in props[:5]:
                lines.append(
                    f"• {p['title']} — {p['city']}, ₹{p['price']:,.0f} "
                    f"({p['bedrooms']}BHK, {p['area_sqft']} sqft)"
                )
            lines.append("\nVisit Search page for filters and details.")
            reply = "\n".join(lines)
        else:
            reply = "No matching properties found. Try another city or browse our listings."
    elif intent == "recommend":
        recs = recommendation.recommend(user_id=user_id, city=city, limit=5)
        lines = ["Here are my top recommendations for you:"]
        for p in recs:
            lines.append(
                f"• {p['title']} — {p['city']}, ₹{p['price']:,.0f}"
            )
        reply = "\n".join(lines) if recs else "No recommendations available yet. Set your preferences in your profile."
    elif intent == "predict":
        nums = _extract_numbers(message)
        area = nums[0] if nums else 1200
        beds = int(nums[1]) if len(nums) > 1 else 2
        result = price_predictor.predict_price(
            area_sqft=area, bedrooms=beds, bathrooms=2,
            city=city or "Bangalore", property_type="apartment",
        )
        reply = (
            f"Estimated price for ~{area} sqft in {city or 'Bangalore'}:\n"
            f"₹{result['predicted_price']:,.0f} "
            f"(~₹{result['price_per_sqft']:,.0f}/sqft, method: {result['method']})"
        )
    elif intent == "emi":
        nums = _extract_numbers(message)
        principal = nums[0] if nums else 5000000
        rate = nums[1] if len(nums) > 1 else 8.5
        years = int(nums[2]) if len(nums) > 2 else 20
        result = emi_calculator.calculate_emi(principal, rate, years * 12)
        reply = (
            f"EMI for ₹{principal:,.0f} at {rate}% for {years} years:\n"
            f"Monthly EMI: ₹{result['emi']:,.0f}\n"
            f"Total interest: ₹{result['total_interest']:,.0f}"
        )
    elif intent == "compare":
        reply = (
            "To compare properties, go to the Compare page and select up to 4 listings, "
            "or tell me property IDs like 'compare 1 and 2'."
        )
        ids = [int(x) for x in re.findall(r"\b(\d+)\b", message)][:4]
        if len(ids) >= 2:
            props = property_model.compare(ids)
            if props:
                lines = ["Property comparison:"]
                for p in props:
                    lines.append(
                        f"#{p['id']} {p['title']}: ₹{p['price']:,.0f}, "
                        f"{p['bedrooms']}BHK, {p['area_sqft']} sqft, {p['city']}"
                    )
                reply = "\n".join(lines)
    elif intent == "visit":
        reply = (
            "You can schedule a site visit from any property detail page, "
            "or visit the Schedule Visit page while logged in."
        )
    else:
        reply = (
            "I'm here to help with property search, recommendations, price prediction, "
            "EMI calculation, comparisons, and site visits. Try asking something like "
            "'Show apartments in Mumbai' or 'Calculate EMI for 50 lakhs'."
        )

    if session_id:
        execute(
            "INSERT INTO chat_messages (user_id, session_id, role, message) VALUES (%s,%s,%s,%s)",
            (user_id, session_id, "user", message),
        )
        execute(
            "INSERT INTO chat_messages (user_id, session_id, role, message) VALUES (%s,%s,%s,%s)",
            (user_id, session_id, "assistant", reply),
        )

    return reply


def new_session_id():
    return str(uuid.uuid4())
