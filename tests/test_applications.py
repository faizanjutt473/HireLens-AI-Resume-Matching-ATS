from app.matching import match_score
from app.models import Job, Resume

from .helpers import BAD_RESUME, GOOD_RESUME, apply_new, docx_bytes, post_job, upload


def test_apply_creates_scored_application(client, make_user, employer):
    job = post_job(client, employer)
    _, application = apply_new(make_user, client, job["id"])
    assert application["stage"] == "applied"
    assert 0 <= application["match_score"] <= 100
    assert application["job_title"] == "Backend Engineer"
    assert set(application["matched"]) == {"Python", "Flask", "PostgreSQL"}
    assert application["missing"] == []


def test_apply_requires_resume(client, employer, candidate):
    job = post_job(client, employer)
    r = client.post("/api/applications", json={"job_id": job["id"]}, headers=candidate["headers"])
    assert r.status_code == 400
    assert "resume" in r.get_json()["message"].lower()


def test_cannot_apply_twice(client, employer, candidate):
    job = post_job(client, employer)
    upload(client, candidate["headers"], docx_bytes(GOOD_RESUME))
    url, body = "/api/applications", {"job_id": job["id"]}
    assert client.post(url, json=body, headers=candidate["headers"]).status_code == 201
    assert client.post(url, json=body, headers=candidate["headers"]).status_code == 409


def test_apply_to_closed_or_missing_job(client, employer, candidate):
    job = post_job(client, employer)
    upload(client, candidate["headers"], docx_bytes(GOOD_RESUME))
    client.patch(f"/api/jobs/{job['id']}", json={"status": "closed"}, headers=employer["headers"])
    h = candidate["headers"]
    assert client.post("/api/applications", json={"job_id": job["id"]}, headers=h).status_code == 404
    assert client.post("/api/applications", json={"job_id": 9999}, headers=h).status_code == 404
    assert client.post("/api/applications", json={}, headers=h).status_code == 400


def test_employer_cannot_apply(client, employer):
    job = post_job(client, employer)
    r = client.post("/api/applications", json={"job_id": job["id"]}, headers=employer["headers"])
    assert r.status_code == 403


def test_my_applications(client, make_user, employer):
    job = post_job(client, employer)
    cand, _ = apply_new(make_user, client, job["id"])
    items = client.get("/api/applications/mine", headers=cand["headers"]).get_json()["applications"]
    assert len(items) == 1 and items[0]["company"] == "Acme Ltd"


def test_scores_endpoint(client, employer, candidate):
    job = post_job(client, employer)
    url = f"/api/applications/scores?job_ids={job['id']},abc"

    before = client.get(url, headers=candidate["headers"]).get_json()
    assert before == {"has_resume": False, "scores": {}}

    upload(client, candidate["headers"], docx_bytes(GOOD_RESUME))
    after = client.get(url, headers=candidate["headers"]).get_json()
    assert after["has_resume"] is True
    entry = after["scores"][str(job["id"])]
    assert 0 <= entry["score"] <= 100 and "Python" in entry["matched"]


def test_scores_endpoint_is_candidate_only(client, employer):
    assert client.get("/api/applications/scores?job_ids=1", headers=employer["headers"]).status_code == 403


def test_better_resume_scores_higher():
    job = Job(
        title="Backend Engineer",
        description="Build Flask APIs with PostgreSQL for a hiring platform.",
        skills=["Python", "Flask", "PostgreSQL"],
    )
    good = Resume(raw_text=GOOD_RESUME, skills=["Python", "Flask", "PostgreSQL", "Docker"])
    bad = Resume(raw_text=BAD_RESUME, skills=[])
    good_score, matched, missing = match_score(job, good)
    bad_score, _, bad_missing = match_score(job, bad)
    assert good_score > bad_score + 20
    assert 0 <= bad_score <= good_score <= 100
    assert matched == ["Python", "Flask", "PostgreSQL"] and missing == []
    assert len(bad_missing) == 3


def test_job_without_required_skills_uses_text_only():
    job = Job(title="Chef", description="Bake bread and cakes in a bakery.", skills=[])
    score, matched, missing = match_score(job, Resume(raw_text=BAD_RESUME, skills=[]))
    assert 0 <= score <= 100 and matched == [] and missing == []