from flask import Blueprint

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")

from . import routes  # noqa: E402,F401