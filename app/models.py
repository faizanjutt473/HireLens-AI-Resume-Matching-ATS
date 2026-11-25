from datetime import datetime, timezone

from sqlalchemy.orm import synonym

from .extensions import bcrypt, db


def utcnow():
    return datetime.now(timezone.utc)


class Role:
    CANDIDATE = "candidate"
    EMPLOYER = "employer"


class JobStatus:
    OPEN = "open"
    CLOSED = "closed"


class Stage:
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    HIRED = "hired"
    REJECTED = "rejected"

    ALL = (APPLIED, SHORTLISTED, INTERVIEW, HIRED, REJECTED)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.CANDIDATE)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    candidate_profile = db.relationship(
        "CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    company = db.relationship(
        "Company", back_populates="owner", uselist=False, cascade="all, delete-orphan"
    )
    resumes = db.relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    applications = db.relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class CandidateProfile(db.Model):
    __tablename__ = "candidate_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    headline = db.Column(db.String(160))
    phone = db.Column(db.String(30))
    location = db.Column(db.String(120))

    user = db.relationship("User", back_populates="candidate_profile")


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    website = db.Column(db.String(255))
    location = db.Column(db.String(120))
    description = db.Column(db.Text)

    owner = db.relationship("User", back_populates="company")
    jobs = db.relationship("Job", back_populates="company", cascade="all, delete-orphan")


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(120))
    job_type = db.Column(db.String(30))  # Full-time, Part-time, Contract
    experience_level = db.Column(db.String(40))
    skills_required = db.Column(db.JSON, default=list)
    skills = synonym("skills_required")  # alias: job.skills aur Job(skills=...) dono chalenge
    embedding = db.Column(db.JSON)  # sentence-transformers vector (match score ke liye)
    status = db.Column(db.String(20), default=JobStatus.OPEN, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    company = db.relationship("Company", back_populates="jobs")
    applications = db.relationship("Application", back_populates="job", cascade="all, delete-orphan")


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(500), nullable=False)
    raw_text = db.Column(db.Text)
    skills = db.Column(db.JSON, default=list)  # NLP/BERT se nikali hui skills
    embedding = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="resumes")


class Application(db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("job_id", "candidate_id", name="uq_application_job_candidate"),
        db.Index("ix_application_job_stage", "job_id", "stage"),
    )

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"))
    match_score = db.Column(db.Float)  # 0 se 100
    stage = db.Column(db.String(20), default=Stage.APPLIED, nullable=False)
    cover_note = db.Column(db.Text)
    applied_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    stage_updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    hired_at = db.Column(db.DateTime(timezone=True))

    job = db.relationship("Job", back_populates="applications")
    candidate = db.relationship("User", back_populates="applications")
    resume = db.relationship("Resume")
    history = db.relationship(
        "StageHistory", back_populates="application", cascade="all, delete-orphan"
    )
    interviews = db.relationship(
        "Interview", back_populates="application", cascade="all, delete-orphan"
    )


class StageHistory(db.Model):
    __tablename__ = "stage_history"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    from_stage = db.Column(db.String(20))
    to_stage = db.Column(db.String(20), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    changed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    application = db.relationship("Application", back_populates="history")


class Interview(db.Model):
    __tablename__ = "interviews"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False)
    duration_minutes = db.Column(db.Integer, default=45)
    location_or_link = db.Column(db.String(255))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="scheduled", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    application = db.relationship("Application", back_populates="interviews")