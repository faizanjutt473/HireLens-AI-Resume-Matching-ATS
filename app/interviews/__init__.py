from flask import Blueprint

interviews_bp = Blueprint("interviews", __name__, url_prefix="/api/interviews")

from . import routes  # noqa: E402,F401