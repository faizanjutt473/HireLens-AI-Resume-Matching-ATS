from marshmallow import Schema, fields, validate


class InterviewSchema(Schema):
    application_id = fields.Int(required=True)
    scheduled_at = fields.DateTime(required=True)
    duration_minutes = fields.Int(load_default=45, validate=validate.Range(min=15, max=240))
    location_or_link = fields.Str(required=True, validate=validate.Length(min=3, max=255))
    notes = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=1000))