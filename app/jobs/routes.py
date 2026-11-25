from flask import jsonify, request
from marshmallow import ValidationError
from sqlalchemy import or_

from ..auth.routes import first_error
from ..extensions import db
from ..models import Company, Job, JobStatus, Role
from ..utils import current_user, role_required
from . import jobs_bp
from .schemas import JobSchema


def clean_skills(skills):
    seen, out = set(), []
    for s in skills or []:
        s = s.strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def job_json(job, owner_view=False):
    data = {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "location": job.location,
        "job_type": job.job_type,
        "experience_level": job.experience_level,
        "skills": job.skills or [],
        "status": job.status,
        "company": job.company.name,
        "created_at": job.created_at.isoformat(),
    }
    if owner_view:
        data["applicants"] = len(job.applications)
    return data


@jobs_bp.get("")
def list_jobs():
    q = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    job_type = request.args.get("type", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 20, type=int), 1), 50)

    query = Job.query.join(Company).filter(Job.status == JobStatus.OPEN)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Job.title.ilike(like),
                Company.name.ilike(like),
                db.cast(Job.skills, db.String).ilike(like),
            )
        )
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if job_type:
        query = query.filter(Job.job_type == job_type)

    result = query.order_by(Job.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify(
        jobs=[job_json(j) for j in result.items],
        total=result.total,
        page=result.page,
        pages=result.pages,
    )


@jobs_bp.get("/mine")
@role_required(Role.EMPLOYER)
def my_jobs():
    user = current_user()
    jobs = (
        Job.query.filter_by(company_id=user.company.id).order_by(Job.created_at.desc()).all()
    )
    return jsonify(jobs=[job_json(j, owner_view=True) for j in jobs])


@jobs_bp.get("/<int:job_id>")
def get_job(job_id):
    job = db.session.get(Job, job_id)
    if not job or job.status != JobStatus.OPEN:
        return jsonify(message="Job not found."), 404
    return jsonify(job=job_json(job))


@jobs_bp.post("")
@role_required(Role.EMPLOYER)
def create_job():
    try:
        data = JobSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    data.pop("status", None)
    data["skills"] = clean_skills(data.get("skills"))
    job = Job(company_id=current_user().company.id, **data)
    db.session.add(job)
    db.session.commit()
    return jsonify(job=job_json(job, owner_view=True)), 201


@jobs_bp.patch("/<int:job_id>")
@role_required(Role.EMPLOYER)
def update_job(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify(message="Job not found."), 404
    if job.company_id != current_user().company.id:
        return jsonify(message="You can only edit your own jobs."), 403

    try:
        data = JobSchema(partial=True).load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    if "skills" in data:
        data["skills"] = clean_skills(data["skills"])
    for key, value in data.items():
        setattr(job, key, value)
    if {"title", "description", "skills"} & data.keys():
        job.embedding = None
    db.session.commit()
    return jsonify(job=job_json(job, owner_view=True))