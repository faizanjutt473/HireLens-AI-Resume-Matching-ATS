from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from ..models import Role


class RegisterSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    role = fields.Str(required=True, validate=validate.OneOf([Role.CANDIDATE, Role.EMPLOYER]))
    company_name = fields.Str(load_default=None, validate=validate.Length(max=160))

    @validates_schema
    def check_company(self, data, **kwargs):
        if data["role"] == Role.EMPLOYER and not (data.get("company_name") or "").strip():
            raise ValidationError("Company name is required for employers.", "company_name")


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)