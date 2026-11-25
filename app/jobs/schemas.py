from marshmallow import Schema, fields, pre_load, validate

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
LEVELS = ["Entry", "Mid", "Senior", "Lead"]


class JobSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=3, max=160))
    description = fields.Str(required=True, validate=validate.Length(min=20, max=8000))
    location = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=120))
    job_type = fields.Str(required=True, validate=validate.OneOf(JOB_TYPES))
    experience_level = fields.Str(
        load_default=None, allow_none=True, validate=validate.OneOf(LEVELS)
    )
    skills = fields.List(
        fields.Str(validate=validate.Length(min=1, max=40)),
        load_default=list,
        validate=validate.Length(max=20),
    )
    status = fields.Str(validate=validate.OneOf(["open", "closed"]))

    @pre_load
    def drop_blank_skills(self, data, **kwargs):
        skills = data.get("skills") if isinstance(data, dict) else None
        if isinstance(skills, list):
            data = {
                **data,
                "skills": [s for s in skills if not (isinstance(s, str) and not s.strip())],
            }
        return data