from flask import Blueprint, render_template, session

from models import property_model
from services import recommendation

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    featured = property_model.search(limit=6)
    return render_template("index.html", properties=featured)


@main_bp.route("/search")
def search_page():
    return render_template("search.html")


@main_bp.route("/property/<int:property_id>")
def property_detail(property_id):
    prop = property_model.get_by_id(property_id)
    if not prop:
        return render_template("404.html"), 404
    images = property_model.get_images(property_id)
    return render_template("property_detail.html", property=prop, images=images)


@main_bp.route("/compare")
def compare_page():
    return render_template("compare.html")


@main_bp.route("/emi")
def emi_page():
    return render_template("emi.html")


@main_bp.route("/chat")
def chat_page():
    if "chat_session_id" not in session:
        from services.chatbot import new_session_id
        session["chat_session_id"] = new_session_id()
    return render_template("chat.html")


@main_bp.route("/schedule-visit")
def schedule_visit_page():
    return render_template("schedule_visit.html")
