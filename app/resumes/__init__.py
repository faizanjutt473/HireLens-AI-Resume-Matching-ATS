from flask import Blueprint

resumes_bp = Blueprint("resumes", __name__, url_prefix="/api/resumes")

from . import routes  # noqa: E402,F401