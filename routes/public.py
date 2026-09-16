import os
import uuid
from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
    jsonify,
)

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
        raw_images = [i["file_path"] for i in media.get("images", []) if i.get("file_path")]
        if row.get("primary_image") and row["primary_image"] not in raw_images:
            raw_images.insert(0, row["primary_image"])
        # Resolve to browser-safe URLs (HTTPS remote or static default — never bare /uploads on Vercel).
        image_urls = []
        for path in raw_images:
            url = prop_model.public_image_url(path)
            if url and url not in image_urls:
                image_urls.append(url)
        if not row.get("primary_image") and raw_images:
            row["primary_image"] = raw_images[0]
            row["primary_image_url"] = prop_model.public_image_url(raw_images[0])
        elif row.get("primary_image"):
            row["primary_image_url"] = prop_model.public_image_url(row.get("primary_image"))
        row["listing_images"] = image_urls
        row["listing_videos"] = [
            prop_model.public_image_url(v["file_path"])
            for v in media.get("videos", [])
            if v.get("file_path")
        ]
        masked.append(row)
    return masked


public_bp = Blueprint("public", __name__)


@public_bp.before_request
def track_visitor():
    if request.endpoint and (
        request.endpoint.startswith("static")
        or request.path.startswith("/static/")
        or request.path.startswith("/uploads/")
    ):
        return
    if "visitor_id" not in session:
        session["visitor_id"] = str(uuid.uuid4())
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    # At most one visitor touch + one page_view event per browser session load
    # (avoids SELECT+UPDATE+INSERT on every navigation — major TTFB cost to Tokyo PG).
    try:
        if not session.get("_visitor_tracked"):
            analytics_model.record_visitor(
                session["visitor_id"], session["session_id"],
                user_agent=request.headers.get("User-Agent", "")[:300],
            )
            session["_visitor_tracked"] = True
        if request.endpoint and not session.get("_pageview_logged"):
            analytics_model.record_event(
                session["visitor_id"], "page_view", meta={"path": request.path}
            )
            session["_pageview_logged"] = True
    except Exception:
        pass


@public_bp.route("/")
def home():
    # Public feed uses the same status set as /properties (available/approved/active).
    featured_properties = _attach_listing_media(
        prop_model.search(limit=9, sort="newest", status="available")
    )
    home_stats = {"properties": 0, "clients": 0, "years": 10}
    try:
        home_stats = analytics_model.home_kpi_counts()
    except Exception:
        pass
    # Live reviews only — normalize to the exact keys home.html expects.
    try:
        raw_reviews = reviews_model.list_reviews(limit=6) or []
    except Exception as exc:
        current_app.logger.exception("home: failed to load reviews: %s", exc)
        print(f"[reviews] home fetch error: {exc}", flush=True)
        raw_reviews = []
    testimonials = []
    for row in raw_reviews:
        try:
            rating = max(1, min(5, int((row or {}).get("rating") or 5)))
        except (TypeError, ValueError):
            rating = 5
        testimonials.append(
            {
                "id": (row or {}).get("id"),
                "client_name": (row or {}).get("client_name")
                or (row or {}).get("name")
                or (row or {}).get("reviewer_name")
                or "Anonymous",
                "client_location": (row or {}).get("client_location")
                or (row or {}).get("location")
                or "Surat",
                "review_text": (row or {}).get("review_text")
                or (row or {}).get("comment")
                or (row or {}).get("text")
                or "",
                "rating": rating,
            }
        )
    print(
        f"[reviews] home rendering {len(testimonials)} review(s); "
        f"sample_keys={list(testimonials[0].keys()) if testimonials else []}",
        flush=True,
    )
    current_app.logger.info("home: rendering %s review(s)", len(testimonials))
    return render_template(
        "public/home.html",
        testimonials=testimonials,
        reviews=testimonials,
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
    # Same public status set as home (`available` / `approved` / `active`).
    sort = (request.args.get("sort") or "newest").strip() or "newest"
    city = (request.args.get("city") or "").strip() or None
    location = (request.args.get("location") or "").strip() or None
    area = (request.args.get("area") or "").strip() or None
    listing_properties = prop_model.search(
        city=city,
        location=location,
        area=area,
        property_type=(request.args.get("type") or "").strip() or None,
        keyword=(request.args.get("q") or "").strip() or None,
        sort=sort,
        status="available",
        limit=120,
    )
    return render_template(
        "public/listings.html",
        areas=prop_model.areas_list(),
        categories=prop_model.categories_summary(),
        properties=listing_properties,
        listing_count=len(listing_properties),
    )


@public_bp.route("/property/<slug>")
def property_detail(slug):
    prop = prop_model.get_by_slug(slug)
    public_statuses = {"available", "approved", "active"}
    if not prop or (prop.get("status") or "").lower() not in public_statuses:
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
@public_bp.route("/visit-request")
def contact():
    property_slug = (request.args.get("property") or "").strip()
    linked_property = None
    if property_slug:
        linked_property = prop_model.get_by_slug(property_slug)
    # Contact Us page always uses inquiry copy (client feedback).
    return render_template(
        "public/contact.html",
        intent="inquiry",
        property_slug=property_slug,
        linked_property=linked_property,
    )


@public_bp.route("/testimonials")
def testimonials():
    rows = reviews_model.list_reviews(limit=120) or []
    for row in rows:
        try:
            row["rating"] = max(1, min(5, int(row.get("rating") or 5)))
        except (TypeError, ValueError):
            row["rating"] = 5
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
            return _sell_error_response(
                "Please fill all mandatory fields before submitting.",
                code=400,
            )

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

        created_property = None
        submission_id = None
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
                return _sell_error_response(
                    "This property already exists in our system and cannot be uploaded again.",
                    code=409,
                )

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
                    "city": (request.form.get("city") or "Surat").strip() or "Surat",
                    "location": (request.form.get("location_area") or area_name or "").strip() or None,
                }
            )

            image_paths = []
            video_paths = []
            media_errors = []
            uploaded_images = [
                f for f in request.files.getlist("images") if f and getattr(f, "filename", None)
            ]
            uploaded_videos = [
                f for f in request.files.getlist("videos") if f and getattr(f, "filename", None)
            ]
            for i, upload in enumerate(uploaded_images):
                try:
                    # Supabase public URL when STORAGE_BACKEND=supabase; else Cloudinary/local.
                    stored = save_upload(upload, created_property["id"], "images", ALLOWED_IMAGE)
                    if stored:
                        prop_model.add_image(
                            created_property["id"], stored, is_primary=(i == 0), sort_order=i
                        )
                        image_paths.append(stored)
                    else:
                        media_errors.append(f"Image {i + 1} was rejected or empty.")
                except Exception as exc:
                    current_app.logger.exception(
                        "sell: image upload failed for property %s: %s",
                        created_property.get("id"),
                        exc,
                    )
                    media_errors.append(str(exc) or "Image upload failed.")

            for i, upload in enumerate(uploaded_videos):
                try:
                    stored = save_upload(upload, created_property["id"], "videos", ALLOWED_VIDEO)
                    if stored:
                        prop_model.add_video(created_property["id"], stored, sort_order=i)
                        video_paths.append(stored)
                    else:
                        media_errors.append(f"Video {i + 1} was rejected or empty.")
                except Exception as exc:
                    current_app.logger.exception(
                        "sell: video upload failed for property %s: %s",
                        created_property.get("id"),
                        exc,
                    )
                    media_errors.append(str(exc) or "Video upload failed.")

            media_warning = None
            if uploaded_images and not image_paths:
                media_warning = (
                    "Your listing was saved, but none of the photos could be uploaded. "
                    "Please try again or contact us to attach photos."
                )
            elif media_errors and image_paths:
                media_warning = (
                    "Listing saved, but some media files failed to upload. "
                    "You can add more photos later via our team."
                )

            submission_id = submission_model.create_submission(
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
                    "location": request.form.get("location_area") or area_name,
                    "location_area": request.form.get("location_area"),
                    "description": request.form.get("description"),
                    "amenities": amenities,
                    "listing_intent": property_status,
                    "images": image_paths,
                    "videos": video_paths,
                }
            )
        except Exception:
            # Only error when the property row itself never landed.
            if created_property:
                return _sell_success_response(
                    created_property,
                    submission_id,
                    image_paths=locals().get("image_paths") or [],
                    media_warning=locals().get("media_warning"),
                )
            return _sell_error_response()

        # Inquiry is best-effort CRM bookkeeping — never override a successful submit.
        try:
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
            pass

        return _sell_success_response(
            created_property,
            submission_id,
            image_paths=image_paths,
            media_warning=media_warning,
        )

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


def _wants_json() -> bool:
    if request.args.get("format") == "json":
        return True
    if (request.headers.get("X-Requested-With") or "").lower() == "xmlhttprequest":
        return True
    accept = (request.headers.get("Accept") or "").lower()
    # Prefer JSON when client asks for it (fetch sell form).
    return "application/json" in accept


def _session_user_id() -> str:
    """Stable per-browser seller id for My Listings (local session UUID)."""
    uid = (session.get("user_id") or "").strip()
    if not uid:
        uid = str(uuid.uuid4())
        session["user_id"] = uid
    return uid


def _attach_user_id(property_id, submission_id=None) -> None:
    uid = _session_user_id()
    from database import execute

    try:
        execute("UPDATE properties SET user_id=%s WHERE id=%s", (uid, property_id))
    except Exception:
        pass
    if submission_id:
        try:
            execute(
                "UPDATE owner_submissions SET user_id=%s WHERE id=%s",
                (uid, submission_id),
            )
        except Exception:
            pass


def _track_my_listing(property_id, owner_mobile: str | None = None) -> None:
    ids = list(session.get("my_listing_ids") or [])
    pid = int(property_id)
    if pid not in ids:
        ids.append(pid)
    session["my_listing_ids"] = ids[-50:]
    if owner_mobile:
        session["my_listings_mobile"] = str(owner_mobile).strip()
    _session_user_id()


def _sell_success_response(created_property, submission_id=None, image_paths=None, media_warning=None):
    _track_my_listing(
        created_property["id"],
        request.form.get("owner_mobile"),
    )
    _attach_user_id(created_property["id"], submission_id)
    image_urls = [
        prop_model.public_image_url(path)
        for path in (image_paths or [])
        if path
    ]
    session["sell_confirm_images"] = image_urls[:12]
    session["sell_confirm_property_id"] = created_property.get("id")
    message = "Property submitted successfully! Our team will review and approve it shortly."
    if media_warning:
        message = f"{message} {media_warning}"
        flash(media_warning, "warning")
    if _wants_json():
        return jsonify({
            "success": True,
            "status": "success",
            "message": message,
            "property_id": created_property.get("id"),
            "property_status": created_property.get("status") or "reserved",
            "user_id": session.get("user_id"),
            "image_urls": image_urls,
            "media_warning": media_warning,
        }), 201
    flash(message, "success")
    return redirect(url_for("public.my_listings"))


def _sell_error_response(message=None, code=400):
    message = message or "Unable to submit property right now. Please try again."
    if _wants_json():
        return jsonify({"success": False, "status": "error", "error": message}), code
    flash(message, "danger")
    return redirect(url_for("public.sell_property"))


@public_bp.route("/my-listings", methods=["GET", "POST"])
@public_bp.route("/dashboard/listings", methods=["GET", "POST"])
@public_bp.route("/dashboard", methods=["GET", "POST"])
def my_listings():
    """User dashboard: track pending / approved / rejected sell submissions by user_id."""
    from database import query_all

    user_id = _session_user_id()
    mobile = (request.values.get("mobile") or session.get("my_listings_mobile") or "").strip()
    if request.method == "POST" and mobile:
        session["my_listings_mobile"] = mobile

    submissions = []
    # Primary filter: session user_id (matches sell-form attach).
    try:
        rows = query_all(
            """SELECT s.*, p.status AS property_current_status, p.slug AS property_slug
               FROM owner_submissions s
               LEFT JOIN properties p ON p.id=s.property_id
               WHERE CAST(s.user_id AS TEXT)=%s
               ORDER BY s.created_at DESC LIMIT 100""",
            (str(user_id),),
        )
        submissions = [submission_model._parse_submission(r) for r in (rows or [])]
    except Exception:
        submissions = []

    # Fallback / merge: owner mobile lookup for legacy rows without user_id.
    if mobile:
        try:
            like = f"%{mobile}%"
            rows = query_all(
                """SELECT s.*, p.status AS property_current_status, p.slug AS property_slug
                   FROM owner_submissions s
                   LEFT JOIN properties p ON p.id=s.property_id
                   WHERE s.owner_mobile LIKE %s OR COALESCE(s.owner_alt_mobile,'') LIKE %s
                   ORDER BY s.created_at DESC LIMIT 100""",
                (like, like),
            )
            by_id = {s.get("id"): s for s in submissions if s.get("id") is not None}
            for r in rows or []:
                parsed = submission_model._parse_submission(r)
                if parsed.get("id") not in by_id:
                    submissions.append(parsed)
        except Exception:
            pass

    tracked_ids = [int(x) for x in (session.get("my_listing_ids") or []) if str(x).isdigit()]
    tracked_props = []
    try:
        props = query_all(
            """SELECT * FROM properties
               WHERE CAST(user_id AS TEXT)=%s
               ORDER BY created_at DESC LIMIT 100""",
            (str(user_id),),
        )
        tracked_props = [prop_model.to_dict(r, public=False) for r in (props or [])]
    except Exception:
        tracked_props = []
    for pid in tracked_ids:
        try:
            row = prop_model.get_by_id(pid)
            if row and all(int(p.get("id") or 0) != int(pid) for p in tracked_props):
                tracked_props.append(prop_model.to_dict(row, public=False))
        except Exception:
            pass

    # Resolve thumbs for submitter visibility (reserved listings are not public).
    try:
        media_map = prop_model.get_media_bulk([p["id"] for p in tracked_props if p.get("id")])
    except Exception:
        media_map = {}
    for p in tracked_props:
        media = media_map.get(p.get("id"), {"images": []})
        paths = [i.get("file_path") for i in media.get("images", []) if i.get("file_path")]
        if p.get("primary_image") and p["primary_image"] not in paths:
            paths.insert(0, p["primary_image"])
        p["thumb_urls"] = [prop_model.public_image_url(path) for path in paths[:6]]

    for s in submissions:
        raw_images = s.get("images") or []
        if isinstance(raw_images, str):
            raw_images = []
        s["thumb_urls"] = [prop_model.public_image_url(path) for path in raw_images[:6] if path]

    confirm_images = list(session.pop("sell_confirm_images", None) or [])
    confirm_property_id = session.pop("sell_confirm_property_id", None)

    return render_template(
        "public/my_listings.html",
        mobile=mobile,
        user_id=user_id,
        submissions=submissions,
        tracked_properties=tracked_props,
        confirm_images=confirm_images,
        confirm_property_id=confirm_property_id,
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
