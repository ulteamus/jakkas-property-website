import os
import uuid
from flask import Blueprint, render_template, request, session, redirect, url_for, flash

from config import ALLOWED_IMAGE, ALLOWED_VIDEO
from models import property as prop_model
from models import analytics as analytics_model
from models import inquiry as inquiry_model
from models import submission as submission_model
from models import reviews as reviews_model
from utils.helpers import save_upload
from services import india_property_predictor


def _attach_listing_media(properties):
    if not properties:
        return properties
    media_map = prop_model.get_media_bulk([p["id"] for p in properties])
    masked = []
    for p in properties:
        row = prop_model.to_dict(p, public=True)
        media = media_map.get(row["id"], {"images": [], "videos": []})
        image_paths = [i["file_path"] for i in media.get("images", []) if i.get("file_path")]
        if row.get("primary_image") and row["primary_image"] not in image_paths:
            image_paths.insert(0, row["primary_image"])
        row["listing_images"] = image_paths
        row["listing_videos"] = [v["file_path"] for v in media.get("videos", []) if v.get("file_path")]
        masked.append(row)
    return masked


public_bp = Blueprint("public", __name__)


@public_bp.before_request
def track_visitor():
    if request.endpoint and request.endpoint.startswith("static"):
        return
    if "visitor_id" not in session:
        session["visitor_id"] = str(uuid.uuid4())
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    try:
        analytics_model.record_visitor(
            session["visitor_id"], session["session_id"],
            user_agent=request.headers.get("User-Agent", "")[:300],
        )
        if request.endpoint:
            analytics_model.record_event(session["visitor_id"], "page_view", meta={"path": request.path})
    except Exception:
        pass


@public_bp.route("/")
def home():
    featured_properties = _attach_listing_media(prop_model.search(limit=9, sort="newest"))
    home_stats = {"properties": 0, "clients": 0, "years": 10}
    try:
        from models import analytics as analytics_model
        dashboard = analytics_model.dashboard_stats()
        home_stats["properties"] = int(dashboard.get("total_properties") or 0)
        home_stats["clients"] = int(dashboard.get("total_inquiries") or 0)
    except Exception:
        pass
    return render_template(
        "public/home.html",
        testimonials=reviews_model.list_reviews(limit=6),
        featured_properties=featured_properties,
        home_stats=home_stats,
    )


@public_bp.route("/about")
def about():
    about_stats = {
        "properties_listed": 0,
        "happy_clients": 0,
        "successful_deals": 0,
        "years_experience": int(os.getenv("COMPANY_YEARS_EXPERIENCE", "10")),
    }
    try:
        dashboard = analytics_model.dashboard_stats()
        reviews_count = len(reviews_model.list_reviews(limit=500))
        about_stats["properties_listed"] = int(dashboard.get("total_properties") or 0)
        about_stats["successful_deals"] = int(
            dashboard.get("sold_properties") or dashboard.get("total_sold") or 0
        )
        about_stats["happy_clients"] = max(
            int(dashboard.get("total_inquiries") or 0),
            int(dashboard.get("total_leads") or 0),
            reviews_count,
        )
    except Exception:
        pass
    return render_template("public/about.html", about_stats=about_stats)


@public_bp.route("/services")
def services():
    return render_template("public/services.html")


@public_bp.route("/properties")
def listings():
    return render_template(
        "public/listings.html",
        areas=prop_model.areas_list(),
        categories=prop_model.categories_summary(),
    )


@public_bp.route("/property/<slug>")
def property_detail(slug):
    prop = prop_model.get_by_slug(slug)
    if not prop or prop.get("status") != "available":
        return render_template("public/404.html"), 404
    try:
        analytics_model.record_property_view(prop["id"], session.get("visitor_id"), session.get("session_id"))
        analytics_model.record_event(session.get("visitor_id"), "property_view", prop["id"])
    except Exception:
        pass
    media = prop_model.get_media(prop["id"])
    similar = prop_model.to_dict_list(prop_model.similar(prop["id"]), public=True)
    from services.whatsapp import interest_message
    wa_link = interest_message(prop["property_name"], prop["area_name"], prop["price"])
    public_prop = prop_model.to_dict(prop, public=True)
    return render_template(
        "public/detail.html",
        property=public_prop,
        media=media,
        similar=similar,
        wa_link=wa_link,
    )


@public_bp.route("/map")
def property_map():
    return render_template("public/map.html")


@public_bp.route("/contact")
def contact():
    return render_template("public/contact.html")


@public_bp.route("/testimonials")
def testimonials():
    rows = reviews_model.list_reviews(limit=120)
    return render_template("public/testimonials.html", testimonials=rows)


@public_bp.route("/sell-property", methods=["GET", "POST"])
@public_bp.route("/list-property", methods=["GET", "POST"])
@public_bp.route("/list-your-property", methods=["GET", "POST"])
def sell_property():
    if request.method == "POST":
        required_fields = [
            "owner_name",
            "owner_mobile",
            "owner_address",
            "property_title",
            "property_type",
            "area_sq_ft",
            "price",
            "property_address",
        ]
        missing = [field for field in required_fields if not request.form.get(field)]
        if missing:
            flash("Please fill all mandatory fields before submitting.", "danger")
            return redirect(url_for("public.sell_property"))

        property_status = (request.form.get("listing_intent") or "sell").strip().lower()
        if property_status not in {"sell", "rent"}:
            property_status = "sell"
        listing_type = "rent" if property_status == "rent" else "sale"
        property_type_raw = (request.form.get("property_type") or "flat").lower()
        property_type = property_type_raw
        if property_type in {"shop", "office", "commercial"}:
            pass
        elif property_type == "apartment":
            property_type = "flat"
        elif property_type == "villa":
            property_type = "bungalow"
        elif property_type == "residential":
            property_type = "flat"

        amenities = request.form.getlist("amenities")
        area_name = request.form.get("location_area") or request.form.get("city") or "Surat"
        apartment_number = (request.form.get("apartment_number") or "").strip() or None
        unit_number = (request.form.get("unit_number") or request.form.get("bungalow_number") or "").strip() or None
        flat_number = (request.form.get("flat_number") or "").strip() or None
        block_wing = (request.form.get("block_wing") or "").strip() or None
        if property_type_raw == "apartment":
            unit_number = unit_number or flat_number or apartment_number
        hide_bhk_types = {"plot", "land", "shop", "office"}
        bhk_value = 0 if property_type_raw in hide_bhk_types else int(request.form.get("bhk") or 0)

        try:
            area_factors = {"sq_ft": 1, "sq_yard": 9, "vigha": 17424, "sq_meter": 10.7639}
            area_sq_ft_raw = request.form.get("area_sq_ft")
            area_unit = (request.form.get("area_unit") or "sq_ft").lower()
            area_value = float(str(request.form.get("area_value") or "0").replace(",", ""))
            if area_sq_ft_raw:
                area_sq_ft = float(str(area_sq_ft_raw).replace(",", ""))
            else:
                area_sq_ft = area_value * area_factors.get(area_unit, 1)
            price = float(str(request.form.get("price")).replace(",", ""))
            submitter_type = (request.form.get("seller_type") or request.form.get("submitter_type") or "owner").lower()
            if submitter_type not in {"owner", "broker", "developer"}:
                submitter_type = "owner"
            duplicate = prop_model.find_duplicate(
                request.form.get("property_title"),
                request.form.get("property_address"),
                area_name,
            )
            if duplicate:
                flash(
                    "This property already exists in our system and cannot be uploaded again.",
                    "warning",
                )
                return redirect(url_for("public.sell_property"))

            created_property = prop_model.create(
                {
                    "property_name": request.form.get("property_title"),
                    "property_type": property_type,
                    "area_name": area_name,
                    "address": request.form.get("property_address"),
                    "price": price,
                    "bhk": bhk_value,
                    "sq_ft": area_sq_ft,
                    "description": request.form.get("description"),
                    "amenities": amenities,
                    "status": "reserved",  # Pending admin approval
                    "is_featured": False,
                    "listing_type": listing_type,
                    "listing_intent": property_status,
                    "seller_type": submitter_type,
                    "block_wing": block_wing,
                    "unit_number": unit_number,
                    "creation_source": "user_submission",
                }
            )

            image_paths = []
            for i, upload in enumerate(request.files.getlist("images")):
                stored = save_upload(upload, created_property["id"], "images", ALLOWED_IMAGE)
                if stored:
                    prop_model.add_image(created_property["id"], stored, is_primary=(i == 0), sort_order=i)
                    image_paths.append(stored)

            video_paths = []
            for i, upload in enumerate(request.files.getlist("videos")):
                stored = save_upload(upload, created_property["id"], "videos", ALLOWED_VIDEO)
                if stored:
                    prop_model.add_video(created_property["id"], stored, sort_order=i)
                    video_paths.append(stored)

            submission_model.create_submission(
                {
                    "property_id": created_property["id"],
                    "owner_name": request.form.get("owner_name"),
                    "owner_mobile": request.form.get("owner_mobile"),
                    "owner_alt_mobile": request.form.get("owner_alt_mobile"),
                    "owner_email": request.form.get("owner_email"),
                    "owner_address": request.form.get("owner_address"),
                    "property_title": request.form.get("property_title"),
                    "property_type": request.form.get("property_type"),
                    "property_status": property_status,
                    "bhk": bhk_value,
                    "bungalow_number": unit_number,
                    "apartment_number": apartment_number or unit_number,
                    "block_wing": block_wing,
                    "unit_number": unit_number,
                    "area_sq_ft": area_sq_ft,
                    "area_unit": area_unit,
                    "area_value": area_value,
                    "price": price,
                    "submitter_type": submitter_type,
                    "seller_type": submitter_type,
                    "property_address": request.form.get("property_address"),
                    "city": request.form.get("city") or "Surat",
                    "location_area": request.form.get("location_area"),
                    "description": request.form.get("description"),
                    "amenities": amenities,
                    "listing_intent": property_status,
                    "images": image_paths,
                    "videos": video_paths,
                }
            )

            inquiry_model.create(
                {
                    "name": request.form.get("owner_name"),
                    "mobile": request.form.get("owner_mobile"),
                    "email": request.form.get("owner_email"),
                    "property_id": created_property["id"],
                    "message": "New property submitted from public Sell Your Property form.",
                    "source": "property_submission",
                    "inquiry_type": "property",
                }
            )
        except Exception:
            flash("Unable to submit property right now. Please try again.", "danger")
            return redirect(url_for("public.sell_property"))

        flash(
            "Thank you! Your property was submitted successfully and is now pending admin approval.",
            "success",
        )
        return redirect(url_for("public.sell_property"))

    return render_template(
        "public/sell_property.html",
        surat_localities=india_property_predictor.list_surat_localities(),
        city_options=[
            "Surat",
            "Ahmedabad",
            "Vadodara",
            "Rajkot",
            "Bhavnagar",
            "Gandhinagar",
            "Bharuch",
            "Navsari",
            "Vapi",
            "Anand",
            "Valsad",
            "Morbi",
        ],
    )


@public_bp.route("/chatbot")
def chatbot():
    return render_template("public/chatbot.html")


@public_bp.route("/ai-chatbot")
def ai_chatbot():
    return redirect(url_for("public.chatbot"))


@public_bp.route("/chat")
def chat_legacy_redirect():
    return redirect(url_for("public.chatbot"))


@public_bp.route("/compare")
def compare():
    return render_template("public/compare.html")


@public_bp.route("/saved")
def saved():
    return render_template("public/saved.html")


@public_bp.route("/price-ai")
@public_bp.route("/price-predictor")
def price_ai_redirect():
    return redirect(url_for("public.chatbot"))
