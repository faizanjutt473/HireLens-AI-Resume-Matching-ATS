from app.extensions import db
from app.models import Job

from .helpers import JOB, post_job


def test_employer_can_post_job(client, employer):
    job = post_job(client, employer)
    assert job["title"] == "Backend Engineer"
    assert job["company"] == "Acme Ltd"
    assert job["status"] == "open"
    assert job["applicants"] == 0


def test_candidate_and_anonymous_cannot_post(client, candidate):
    assert client.post("/api/jobs", json=JOB, headers=candidate["headers"]).status_code == 403
    assert client.post("/api/jobs", json=JOB).status_code == 401


def test_job_validation(client, employer):
    r = client.post("/api/jobs", json={**JOB, "description": "too short"}, headers=employer["headers"])
    assert r.status_code == 400
    r = client.post("/api/jobs", json={**JOB, "job_type": "Gig"}, headers=employer["headers"])
    assert r.status_code == 400


def test_skills_are_deduplicated(client, employer):
    job = post_job(client, employer, skills=["Python", "python", " Flask ", ""])
    assert job["skills"] == ["Python", "Flask"]


def test_public_list_and_pagination(client, employer):
    for i in range(3):
        post_job(client, employer, title=f"Job number {i}")
    data = client.get("/api/jobs?per_page=2").get_json()
    assert data["total"] == 3 and data["pages"] == 2 and len(data["jobs"]) == 2


def test_search_and_filters(client, employer):
    post_job(client, employer)
    post_job(
        client, employer, title="Graphic Designer", skills=["Figma"], location="Lahore", job_type="Contract"
    )
    get = lambda qs: client.get("/api/jobs?" + qs).get_json()["total"]
    assert get("q=figma") == 1
    assert get("q=flask") == 1
    assert get("q=acme") == 2
    assert get("location=lahore") == 1
    assert get("type=Contract") == 1
    assert get("q=nothing-matches-this") == 0


def test_closed_jobs_are_hidden(client, employer):
    job = post_job(client, employer)
    r = client.patch(f"/api/jobs/{job['id']}", json={"status": "closed"}, headers=employer["headers"])
    assert r.status_code == 200 and r.get_json()["job"]["status"] == "closed"
    assert client.get("/api/jobs").get_json()["total"] == 0
    assert client.get(f"/api/jobs/{job['id']}").status_code == 404
    mine = client.get("/api/jobs/mine", headers=employer["headers"]).get_json()["jobs"]
    assert len(mine) == 1 and mine[0]["status"] == "closed"


def test_get_single_job(client, employer):
    job = post_job(client, employer)
    assert client.get(f"/api/jobs/{job['id']}").get_json()["job"]["title"] == job["title"]
    assert client.get("/api/jobs/9999").status_code == 404


def test_only_owner_can_edit(client, make_user, employer, candidate):
    job = post_job(client, employer)
    other = make_user("employer")
    url = f"/api/jobs/{job['id']}"
    assert client.patch(url, json={"title": "Hacked title"}, headers=other["headers"]).status_code == 403
    assert client.patch(url, json={"title": "Hacked title"}, headers=candidate["headers"]).status_code == 403
    assert client.patch("/api/jobs/9999", json={"title": "Whatever"}, headers=employer["headers"]).status_code == 404
    assert client.patch(url, json={"title": "ab"}, headers=employer["headers"]).status_code == 400


def test_editing_text_resets_embedding(app, client, employer):
    job = post_job(client, employer)
    with app.app_context():
        db.session.get(Job, job["id"]).embedding = [0.1, 0.2]
        db.session.commit()
    r = client.patch(f"/api/jobs/{job['id']}", json={"title": "Senior Backend Engineer"}, headers=employer["headers"])
    assert r.status_code == 200
    with app.app_context():
        assert db.session.get(Job, job["id"]).embedding is None


def test_my_jobs_is_employer_only(client, employer, candidate):
    assert client.get("/api/jobs/mine", headers=candidate["headers"]).status_code == 403
    assert client.get("/api/jobs/mine", headers=employer["headers"]).get_json()["jobs"] == []