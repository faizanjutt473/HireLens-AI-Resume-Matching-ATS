from collections import Counter
from datetime import timedelta
from zoneinfo import ZoneInfo

from flask import current_app, jsonify
from sqlalchemy.orm import selectinload

from ..models import Application, Job, JobStatus, Role, Stage, utcnow
from ..utils import current_user, role_required
from . import analytics_bp

FUNNEL = [Stage.APPLIED, Stage.SHORTLISTED, Stage.INTERVIEW, Stage.HIRED]


def count_skills(skill_lists, limit=8):
    counts, names = Counter(), {}
    for skills in skill_lists:
        seen = set()
        for s in skills or []:
            key = s.strip().lower()
            if key and key not in seen:
                seen.add(key)
                names.setdefault(key, s.strip())
                counts[key] += 1
    return [{"skill": names[k], "count": c} for k, c in counts.most_common(limit)]


def average(values):
    return round(sum(values) / len(values), 2) if values else None


def days_to_hire(a):
    return (a.hired_at - a.applied_at).total_seconds() / 86400


@analytics_bp.get("/employer")
@role_required(Role.EMPLOYER)
def employer_analytics():
    company_id = current_user().company.id
    jobs = Job.query.filter_by(company_id=company_id).all()
    apps = (
        Application.query.join(Job)
        .filter(Job.company_id == company_id)
        .options(selectinload(Application.history), selectinload(Application.resume))
        .all()
    )

    # Funnel: har candidate ko us stage tak gina jata hai jahan tak wo kabhi pahuncha
    furthest = []
    for a in apps:
        reached = {h.to_stage for h in a.history} | {a.stage}
        furthest.append(max((FUNNEL.index(s) for s in reached if s in FUNNEL), default=0))
    funnel = [{"stage": s, "count": sum(f >= i for f in furthest)} for i, s in enumerate(FUNNEL)]

    hired = [a for a in apps if a.stage == Stage.HIRED and a.hired_at]
    scores = [a.match_score for a in apps if a.match_score is not None]

    per_job = []
    for j in jobs:
        job_apps = [a for a in apps if a.job_id == j.id]
        job_hired = [a for a in job_apps if a.stage == Stage.HIRED and a.hired_at]
        per_job.append(
            {
                "id": j.id,
                "title": j.title,
                "status": j.status,
                "applicants": len(job_apps),
                "hired": len(job_hired),
                "avg_days_to_hire": average([days_to_hire(a) for a in job_hired]),
            }
        )

    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    today = utcnow().astimezone(tz).date()
    per_day = Counter(a.applied_at.astimezone(tz).date() for a in apps)
    timeline = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        timeline.append({"date": day.isoformat(), "count": per_day.get(day, 0)})

    market_jobs = Job.query.filter_by(status=JobStatus.OPEN).all()

    return jsonify(
        summary={
            "jobs": len(jobs),
            "open_jobs": sum(j.status == JobStatus.OPEN for j in jobs),
            "applicants": len(apps),
            "hired": len(hired),
            "rejected": sum(a.stage == Stage.REJECTED for a in apps),
            "avg_match": average(scores),
            "avg_days_to_hire": average([days_to_hire(a) for a in hired]),
        },
        funnel=funnel,
        per_job=per_job,
        timeline=timeline,
        demand_yours=count_skills(j.skills for j in jobs),
        demand_market=count_skills(j.skills for j in market_jobs),
        applicant_skills=count_skills(a.resume.skills for a in apps if a.resume),
    )