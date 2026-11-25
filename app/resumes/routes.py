import os
import uuid

from flask import current_app, jsonify, request
from marshmallow import Schema, ValidationError, fields, validate
from werkzeug.utils import secure_filename

from ..auth.routes import first_error
from ..extensions import db
from ..models import Application, Resume, Role
from ..utils import current_user, role_required
from . import resumes_bp
from .parser import extract_skills, extract_text

ALLOWED = {"pdf", "docx"}
MAX_RESUMES = 5


class ResumeUpdateSchema(Schema):
    skills = fields.List(
        fields.Str(validate=validate.Length(min=1, max=40)), validate=validate.Length(max=40)
    )
    is_active = fields.Bool(validate=validate.OneOf([True]))


def resume_json(r):
    return {
        "id": r.id,
        "filename": r.filename,
        "skills": r.skills or [],
        "is_active": r.is_active,
        "uploaded_at": r.uploaded_at.isoformat(),
    }


def file_path(r):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], r.stored_path)


def remove_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


def clean_skills(skills):
    seen, out = set(), []
    for s in skills:
        s = s.strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def own_resume(resume_id):
    return Resume.query.filter_by(id=resume_id, user_id=current_user().id).first()


@resumes_bp.get("")
@role_required(Role.CANDIDATE)
def list_resumes():
    items = (
        Resume.query.filter_by(user_id=current_user().id).order_by(Resume.uploaded_at.desc()).all()
    )
    return jsonify(resumes=[resume_json(r) for r in items])


@resumes_bp.post("")
@role_required(Role.CANDIDATE)
def upload_resume():
    user = current_user()
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(message="Choose a resume file to upload."), 400

    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ALLOWED:
        return jsonify(message="Upload a PDF or Word (.docx) file."), 400

    head = f.stream.read(4)
    f.stream.seek(0)
    if (ext == "pdf" and head != b"%PDF") or (ext == "docx" and head != b"PK\x03\x04"):
        return jsonify(message="This file does not look like a valid resume."), 400

    if Resume.query.filter_by(user_id=user.id).count() >= MAX_RESUMES:
        return jsonify(message="You can keep up to 5 resumes. Delete one first."), 400

    stored = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored)
    f.save(path)

    try:
        text = extract_text(path, ext)
    except Exception:
        remove_file(path)
        return jsonify(message="We could not read this file. Try another copy."), 422
    if len(text.strip()) < 50:
        remove_file(path)
        return jsonify(message="No readable text found. Scanned PDFs are not supported yet."), 422

    Resume.query.filter_by(user_id=user.id, is_active=True).update({"is_active": False})
    resume = Resume(
        user_id=user.id,
        filename=secure_filename(f.filename) or f"resume.{ext}",
        stored_path=stored,
        raw_text=text,
        skills=extract_skills(text),
        is_active=True,
    )
    db.session.add(resume)
    db.session.commit()
    return jsonify(resume=resume_json(resume)), 201


@resumes_bp.patch("/<int:resume_id>")
@role_required(Role.CANDIDATE)
def update_resume(resume_id):
    resume = own_resume(resume_id)
    if not resume:
        return jsonify(message="Resume not found."), 404
    try:
        data = ResumeUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(message=first_error(err.messages), errors=err.messages), 400

    if "skills" in data:
        resume.skills = clean_skills(data["skills"])
    if data.get("is_active"):
        Resume.query.filter_by(user_id=resume.user_id, is_active=True).update({"is_active": False})
        resume.is_active = True
    db.session.commit()
    return jsonify(resume=resume_json(resume))


@resumes_bp.delete("/<int:resume_id>")
@role_required(Role.CANDIDATE)
def delete_resume(resume_id):
    resume = own_resume(resume_id)
    if not resume:
        return jsonify(message="Resume not found."), 404

    was_active, user_id, path = resume.is_active, resume.user_id, file_path(resume)
    Application.query.filter_by(resume_id=resume.id).update({"resume_id": None})
    db.session.delete(resume)
    db.session.commit()
    remove_file(path)

    if was_active:
        latest = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
        if latest:
            latest.is_active = True
            db.session.commit()
    return jsonify(message="Resume deleted.")