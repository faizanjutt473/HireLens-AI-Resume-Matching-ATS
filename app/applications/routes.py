from flask import jsonify, request
from marshmallow import Schema, ValidationError, fields, validate
from sqlalchemy.exc import IntegrityError

from ..auth.routes import first_error
from ..extensions import db
from ..matching import match_score
from ..models import Application, Job, JobStatus, Resume, Role, Stage, StageHistory
from ..utils import current_user, role_required
from . import applications_bp


class ApplySchema(Schema):
    job_id = fields.Int(required=True)
    cover_note = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=2000))


def application_json(a):
    return {
        "id": a.id,
        "job_id": a.job_id,
        "job_title": a.job.title,
        "company": a.job.company.name,
        "stage": a.stage,
        "match_score": a.match_score,
        "applied_at": a.applied_at.isoformat(),
    }


def active_resume(user):
    return Resume.query.filter_by(user_id=user.id, is_active=True).first()


@applications_bp.post("")
@role_required(Role.CANDIDATE)
def apply():
    try:
        data = ApplySchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    user = current_user()
    job = db.session.get(Job, data["job_id"])
    if not job or job.status != JobStatus.OPEN:
        return jsonify(message="This job is no longer open."), 404

    resume = active_resume(user)
    if not resume:
        return jsonify(message="Upload a resume before applying."), 400

    if Application.query.filter_by(job_id=job.id, candidate_id=user.id).first():
        return jsonify(message="You have already applied to this job."), 409

    score, matched, missing = match_score(job, resume)
    application = Application(
        job_id=job.id,
        candidate_id=user.id,
        resume_id=resume.id,
        match_score=score,
        stage=Stage.APPLIED,
        cover_note=data["cover_note"],
    )
    application.history.append(
        StageHistory(from_stage=None, to_stage=Stage.APPLIED, changed_by_id=user.id)
    )
    db.session.add(application)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(message="You have already applied to this job."), 409

    body = application_json(application)
    body.update(matched=matched, missing=missing)
    return jsonify(application=body), 201


@applications_bp.get("/mine")
@role_required(Role.CANDIDATE)
def my_applications():
    apps = (
        Application.query.filter_by(candidate_id=current_user().id)
        .order_by(Application.applied_at.desc())
        .all()
    )
    return jsonify(applications=[application_json(a) for a in apps])


@applications_bp.get("/scores")
@role_required(Role.CANDIDATE)
def scores():
    """Jobs page ki rings ke liye: ?job_ids=1,2,3"""
    ids = []
    for part in request.args.get("job_ids", "").split(","):
        if part.strip().isdigit():
            ids.append(int(part))
    ids = ids[:50]

    resume = active_resume(current_user())
    if not resume:
        return jsonify(has_resume=False, scores={})

    jobs = Job.query.filter(Job.id.in_(ids), Job.status == JobStatus.OPEN).all() if ids else []
    result = {}
    for job in jobs:
        score, matched, missing = match_score(job, resume)
        result[str(job.id)] = {"score": score, "matched": matched, "missing": missing}
    db.session.commit()  # naye embeddings cache ho jayein
    return jsonify(has_resume=True, scores=result)