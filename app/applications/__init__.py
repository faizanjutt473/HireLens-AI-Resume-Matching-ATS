from flask import Blueprint

applications_bp = Blueprint("applications", __name__, url_prefix="/api/applications")

from . import routes  # noqa: E402,F401