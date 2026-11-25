from flask import Blueprint

pipeline_bp = Blueprint("pipeline", __name__, url_prefix="/api/pipeline")

from . import routes  # noqa: E402,F401