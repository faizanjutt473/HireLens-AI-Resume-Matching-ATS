from flask import current_app, jsonify, request, send_from_directory
from marshmallow import Schema, ValidationError, fields, validate

from ..auth.routes import first_error
from ..extensions import db
from ..models import Application, Job, Role, Stage, StageHistory, utcnow
from ..utils import current_user, role_required
from . import pipeline_bp


class StageSchema(Schema):
    stage = fields.Str(required=True, validate=validate.OneOf(list(Stage.ALL)))


def owned_job(job_id):
    return Job.query.filter_by(id=job_id, company_id=current_user().company.id).first()


def owned_application(app_id):
    return (
        Application.query.join(Job)
        .filter(Application.id == app_id, Job.company_id == current_user().company.id)
        .first()
    )


def applicant_json(a):
    have = {s.lower() for s in (a.resume.skills or [])} if a.resume else set()
    required = a.job.skills or []
    matched = [s for s in required if s.lower() in have]
    return {
        "id": a.id,
        "candidate_name": a.candidate.full_name,
        "email": a.candidate.email,
        "stage": a.stage,
        "match_score": a.match_score,
        "applied_at": a.applied_at.isoformat(),
        "matched": matched[:6],
        "has_resume": a.resume is not None,
    }


@pipeline_bp.get("/jobs/<int:job_id>")
@role_required(Role.EMPLOYER)
def job_pipeline(job_id):
    job = owned_job(job_id)
    if not job:
        return jsonify(message="Job not found."), 404

    apps = (
        Application.query.filter_by(job_id=job.id)
        .order_by(Application.match_score.desc().nullslast(), Application.applied_at)
        .all()
    )
    hired = [a for a in apps if a.stage == Stage.HIRED and a.hired_at]
    days = [(a.hired_at - a.applied_at).total_seconds() / 86400 for a in hired]
    stats = {
        "total": len(apps),
        "shortlisted": sum(a.stage in (Stage.SHORTLISTED, Stage.INTERVIEW, Stage.HIRED) for a in apps),
        "hired": sum(a.stage == Stage.HIRED for a in apps),
        "avg_days_to_hire": round(sum(days) / len(days), 1) if days else None,
    }
    return jsonify(
        job={"id": job.id, "title": job.title, "status": job.status},
        applicants=[applicant_json(a) for a in apps],
        stats=stats,
    )


@pipeline_bp.patch("/applications/<int:app_id>/stage")
@role_required(Role.EMPLOYER)
def change_stage(app_id):
    application = owned_application(app_id)
    if not application:
        return jsonify(message="Application not found."), 404
    try:
        data = StageSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    new, old = data["stage"], application.stage
    if new == old:
        return jsonify(application=applicant_json(application))

    now = utcnow()
    application.stage = new
    application.stage_updated_at = now
    application.hired_at = now if new == Stage.HIRED else None
    application.history.append(
        StageHistory(from_stage=old, to_stage=new, changed_by_id=current_user().id)
    )
    db.session.commit()
    return jsonify(application=applicant_json(application))


@pipeline_bp.get("/applications/<int:app_id>/resume")
@role_required(Role.EMPLOYER)
def applicant_resume(app_id):
    application = owned_application(app_id)
    if not application or not application.resume:
        return jsonify(message="Resume not found."), 404
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        application.resume.stored_path,
        download_name=application.resume.filename,
    )