from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from .extensions import db
from .models import User


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


def role_required(*roles):
    """Route ko sirf given roles ke liye kholta hai."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if get_jwt().get("role") not in roles:
                return jsonify(message="You do not have access to this resource."), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator