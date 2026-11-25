from app.models import StageHistory
from app.extensions import db

from .helpers import BAD_RESUME, GOOD_RESUME, apply_new, post_job, set_stage


def board(client, employer, job_id):
    return client.get(f"/api/pipeline/jobs/{job_id}", headers=employer["headers"])


def test_best_match_is_listed_first(client, make_user, employer):
    job = post_job(client, employer)
    _, weak = apply_new(make_user, client, job["id"], BAD_RESUME)
    _, strong = apply_new(make_user, client, job["id"], GOOD_RESUME)
    data = board(client, employer, job["id"]).get_json()
    assert [a["id"] for a in data["applicants"]] == [strong["id"], weak["id"]]
    assert data["stats"]["total"] == 2
    assert data["stats"]["hired"] == 0 and data["stats"]["avg_days_to_hire"] is None


def test_move_between_stages_and_stats(client, make_user, employer):
    job = post_job(client, employer)
    _, a = apply_new(make_user, client, job["id"])

    assert set_stage(client, employer, a["id"], "shortlisted")["stage"] == "shortlisted"
    assert board(client, employer, job["id"]).get_json()["stats"]["shortlisted"] == 1

    set_stage(client, employer, a["id"], "hired")
    stats = board(client, employer, job["id"]).get_json()["stats"]
    assert stats["hired"] == 1 and stats["avg_days_to_hire"] is not None

    set_stage(client, employer, a["id"], "applied")
    stats = board(client, employer, job["id"]).get_json()["stats"]
    assert stats["hired"] == 0 and stats["avg_days_to_hire"] is None


def test_stage_changes_are_recorded(app, client, make_user, employer):
    job = post_job(client, employer)
    _, a = apply_new(make_user, client, job["id"])
    set_stage(client, employer, a["id"], "shortlisted")
    set_stage(client, employer, a["id"], "shortlisted")  # same stage: kuch record nahi hona chahiye
    with app.app_context():
        rows = StageHistory.query.filter_by(application_id=a["id"]).order_by(StageHistory.id).all()
        assert [(r.from_stage, r.to_stage) for r in rows] == [(None, "applied"), ("applied", "shortlisted")]


def test_invalid_stage_and_unknown_application(client, make_user, employer):
    job = post_job(client, employer)
    _, a = apply_new(make_user, client, job["id"])
    h = employer["headers"]
    assert client.patch(f"/api/pipeline/applications/{a['id']}/stage", json={"stage": "flying"}, headers=h).status_code == 400
    assert client.patch("/api/pipeline/applications/9999/stage", json={"stage": "hired"}, headers=h).status_code == 404


def test_other_employer_and_candidate_are_blocked(client, make_user, employer):
    job = post_job(client, employer)
    cand, a = apply_new(make_user, client, job["id"])
    other = make_user("employer")

    assert board(client, other, job["id"]).status_code == 404
    r = client.patch(f"/api/pipeline/applications/{a['id']}/stage", json={"stage": "hired"}, headers=other["headers"])
    assert r.status_code == 404
    assert client.get(f"/api/pipeline/jobs/{job['id']}", headers=cand["headers"]).status_code == 403
    assert board(client, employer, 9999).status_code == 404


def test_employer_can_open_applicant_resume(client, make_user, employer):
    job = post_job(client, employer)
    _, a = apply_new(make_user, client, job["id"])
    other = make_user("employer")
    url = f"/api/pipeline/applications/{a['id']}/resume"

    r = client.get(url, headers=employer["headers"])
    assert r.status_code == 200
    assert r.data.startswith(b"PK")
    assert "resume.docx" in r.headers["Content-Disposition"]
    assert client.get(url, headers=other["headers"]).status_code == 404