from flask import jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required
from marshmallow import ValidationError

from ..extensions import db
from ..models import CandidateProfile, Company, Role, User
from ..utils import current_user, role_required
from . import auth_bp
from .schemas import LoginSchema, RegisterSchema


def user_json(user):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "company": user.company.name if user.company else None,
    }


def token_response(user):
    claims = {"role": user.role}
    return {
        "access_token": create_access_token(identity=str(user.id), additional_claims=claims),
        "refresh_token": create_refresh_token(identity=str(user.id), additional_claims=claims),
        "user": user_json(user),
    }


def first_error(errors):
    for value in errors.values():
        return value[0] if isinstance(value, list) else str(value)
    return "Invalid data."


@auth_bp.post("/register")
def register():
    try:
        data = RegisterSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify(message="An account with this email already exists."), 409

    user = User(full_name=data["full_name"].strip(), email=email, role=data["role"])
    user.set_password(data["password"])
    if user.role == Role.EMPLOYER:
        user.company = Company(name=data["company_name"].strip())
    else:
        user.candidate_profile = CandidateProfile()

    db.session.add(user)
    db.session.commit()
    return jsonify(token_response(user)), 201


@auth_bp.post("/login")
def login():
    try:
        data = LoginSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    user = User.query.filter_by(email=data["email"].strip().lower()).first()
    if not user or not user.check_password(data["password"]):
        return jsonify(message="Incorrect email or password."), 401
    if not user.is_active:
        return jsonify(message="This account is disabled."), 403
    return jsonify(token_response(user))


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user = current_user()
    if not user or not user.is_active:
        return jsonify(message="Account not available."), 401
    return jsonify(access_token=token_response(user)["access_token"])


@auth_bp.get("/me")
@jwt_required()
def me():
    return jsonify(user=user_json(current_user()))


# Sirf role-based access check karne ke liye, baad mein hata denge
@auth_bp.get("/employer-check")
@role_required(Role.EMPLOYER)
def employer_check():
    return jsonify(message="Employer access OK")