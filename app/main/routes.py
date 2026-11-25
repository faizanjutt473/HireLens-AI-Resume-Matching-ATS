from flask import abort, jsonify, render_template
from sqlalchemy import text

from ..extensions import db
from . import main_bp

PAGES = {"index", "login", "register", "jobs", "candidate", "employer"}


@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.route("/<page>.html")
def page(page):
    if page not in PAGES:
        abort(404)
    return render_template(f"{page}.html")


@main_bp.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok", database="connected")
    except Exception as exc:
        return jsonify(status="error", database="unreachable", detail=str(exc)), 503