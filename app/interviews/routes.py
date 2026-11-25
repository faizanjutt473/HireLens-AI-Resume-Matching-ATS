from datetime import timedelta, timezone

from flask import jsonify, request
from marshmallow import ValidationError

from ..auth.routes import first_error
from ..emails import fmt_time, queue_email
from ..extensions import db
from ..models import Application, Interview, Job, Role, Stage, StageHistory, utcnow
from ..utils import current_user, role_required
from . import interviews_bp
from .schemas import InterviewSchema


def interview_json(i):
    a = i.application
    return {
        "id": i.id,
        "application_id": a.id,
        "scheduled_at": i.scheduled_at.isoformat(),
        "duration_minutes": i.duration_minutes,
        "location_or_link": i.location_or_link,
        "notes": i.notes,
        "status": i.status,
        "job_title": a.job.title,
        "company": a.job.company.name,
        "candidate_name": a.candidate.full_name,
    }


@interviews_bp.post("")
@role_required(Role.EMPLOYER)
def schedule():
    try:
        data = InterviewSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    user = current_user()
    application = (
        Application.query.join(Job)
        .filter(Application.id == data["application_id"], Job.company_id == user.company.id)
        .first()
    )
    if not application:
        return jsonify(message="Application not found."), 404
    if application.stage in (Stage.HIRED, Stage.REJECTED):
        return jsonify(message="This candidate is already hired or rejected."), 400

    when = data["scheduled_at"]
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when < utcnow() + timedelta(minutes=5):
        return jsonify(message="Pick a time in the future."), 400

    interview = Interview(
        application_id=application.id,
        scheduled_at=when,
        duration_minutes=data["duration_minutes"],
        location_or_link=data["location_or_link"].strip(),
        notes=data["notes"],
    )
    if application.stage != Stage.INTERVIEW:
        old = application.stage
        application.stage = Stage.INTERVIEW
        application.stage_updated_at = utcnow()
        application.hired_at = None
        application.history.append(
            StageHistory(from_stage=old, to_stage=Stage.INTERVIEW, changed_by_id=user.id)
        )
    db.session.add(interview)
    db.session.commit()

    job = application.job
    queue_email(
        application.candidate.email,
        f"Interview invitation: {job.title} at {job.company.name}",
        f"Hi {application.candidate.full_name},\n\n"
        f"{job.company.name} would like to interview you for the {job.title} role.\n\n"
        f"When: {fmt_time(when)}\n"
        f"Duration: {interview.duration_minutes} minutes\n"
        f"Where: {interview.location_or_link}\n"
        + (f"\nNote from the employer:\n{interview.notes}\n" if interview.notes else "")
        + "\nGood luck!\nHireLens",
    )
    return jsonify(interview=interview_json(interview)), 201


@interviews_bp.get("/upcoming")
@role_required(Role.EMPLOYER)
def upcoming_for_employer():
    items = (
        Interview.query.join(Application).join(Job)
        .filter(
            Job.company_id == current_user().company.id,
            Interview.status == "scheduled",
            Interview.scheduled_at >= utcnow(),
        )
        .order_by(Interview.scheduled_at)
        .all()
    )
    return jsonify(interviews=[interview_json(i) for i in items])


@interviews_bp.get("/mine")
@role_required(Role.CANDIDATE)
def mine():
    items = (
        Interview.query.join(Application)
        .filter(
            Application.candidate_id == current_user().id,
            Interview.status == "scheduled",
            Interview.scheduled_at >= utcnow(),
        )
        .order_by(Interview.scheduled_at)
        .all()
    )
    return jsonify(interviews=[interview_json(i) for i in items])


@interviews_bp.post("/<int:interview_id>/cancel")
@role_required(Role.EMPLOYER)
def cancel(interview_id):
    interview = (
        Interview.query.join(Application).join(Job)
        .filter(Interview.id == interview_id, Job.company_id == current_user().company.id)
        .first()
    )
    if not interview:
        return jsonify(message="Interview not found."), 404
    if interview.status != "scheduled":
        return jsonify(message="This interview is already cancelled."), 400

    interview.status = "cancelled"
    db.session.commit()

    a = interview.application
    queue_email(
        a.candidate.email,
        f"Interview cancelled: {a.job.title} at {a.job.company.name}",
        f"Hi {a.candidate.full_name},\n\n"
        f"Your interview for {a.job.title} at {a.job.company.name}, planned for "
        f"{fmt_time(interview.scheduled_at)}, has been cancelled. "
        "The employer may contact you with a new time.\n\nHireLens",
    )
    return jsonify(interview=interview_json(interview))