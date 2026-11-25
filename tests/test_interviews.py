from datetime import datetime, timedelta, timezone

from .helpers import apply_new, future_iso, post_job, set_stage


def book(client, employer, app_id, **over):
    body = {
        "application_id": app_id,
        "scheduled_at": future_iso(),
        "duration_minutes": 30,
        "location_or_link": "https://meet.google.com/abc-defg-hij",
        "notes": "Please keep your camera on.",
        **over,
    }
    return client.post("/api/interviews", json=body, headers=employer["headers"])


def stage_of(client, employer, job_id, app_id):
    apps = client.get(f"/api/pipeline/jobs/{job_id}", headers=employer["headers"]).get_json()["applicants"]
    return next(a["stage"] for a in apps if a["id"] == app_id)


def test_schedule_moves_candidate_and_sends_email(client, make_user, employer, sent):
    job = post_job(client, employer)
    cand, a = apply_new(make_user, client, job["id"])

    r = book(client, employer, a["id"])
    assert r.status_code == 201
    assert r.get_json()["interview"]["status"] == "scheduled"
    assert stage_of(client, employer, job["id"], a["id"]) == "interview"

    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == cand["email"] and "Backend Engineer" in subject
    assert "meet.google.com" in body and "Please keep your camera on." in body


def test_both_sides_see_upcoming_interview(client, make_user, employer, sent):
    job = post_job(client, employer)
    cand, a = apply_new(make_user, client, job["id"])
    book(client, employer, a["id"])

    mine = client.get("/api/interviews/mine", headers=cand["headers"]).get_json()["interviews"]
    theirs = client.get("/api/interviews/upcoming", headers=employer["headers"]).get_json()["interviews"]
    assert len(mine) == 1 and mine[0]["company"] == "Acme Ltd"
    assert len(theirs) == 1 and theirs[0]["candidate_name"] == "Test User"


def test_validation(client, make_user, employer, sent):
    job = post_job(client, employer)
    _, a = apply_new(make_user, client, job["id"])
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    assert book(client, employer, a["id"], scheduled_at=past).status_code == 400
    assert book(client, employer, a["id"], location_or_link="").status_code == 400
    assert book(client, employer, a["id"], duration_minutes=5).status_code == 400
    assert book(client, employer, a["id"], scheduled_at="not a date").status_code == 400
    assert book(client, employer, 9999).status_code == 404
    assert sent == []


def test_cannot_interview_hired_candidate(client, make_user, employer, sent):
    job = post_job(client, employer)
    _, a = apply_new(make_user, client, job["id"])
    set_stage(client, employer, a["id"], "hired")
    assert book(client, employer, a["id"]).status_code == 400


def test_other_employer_and_candidate_blocked(client, make_user, employer, sent):
    job = post_job(client, employer)
    cand, a = apply_new(make_user, client, job["id"])
    other = make_user("employer")
    assert book(client, other, a["id"]).status_code == 404
    assert book(client, {"headers": cand["headers"]}, a["id"]).status_code == 403
    assert client.get("/api/interviews/upcoming", headers=cand["headers"]).status_code == 403
    assert client.get("/api/interviews/mine", headers=employer["headers"]).status_code == 403


def test_cancel_interview(client, make_user, employer, sent):
    job = post_job(client, employer)
    cand, a = apply_new(make_user, client, job["id"])
    interview_id = book(client, employer, a["id"]).get_json()["interview"]["id"]
    url = f"/api/interviews/{interview_id}/cancel"

    r = client.post(url, headers=employer["headers"])
    assert r.status_code == 200 and r.get_json()["interview"]["status"] == "cancelled"
    assert len(sent) == 2 and "cancelled" in sent[1][1].lower()
    assert client.get("/api/interviews/upcoming", headers=employer["headers"]).get_json()["interviews"] == []
    assert client.get("/api/interviews/mine", headers=cand["headers"]).get_json()["interviews"] == []
    assert client.post(url, headers=employer["headers"]).status_code == 400


def test_other_employer_cannot_cancel(client, make_user, employer, sent):
    job = post_job(client, employer)
    _, a = apply_new(make_user, client, job["id"])
    interview_id = book(client, employer, a["id"]).get_json()["interview"]["id"]
    other = make_user("employer")
    assert client.post(f"/api/interviews/{interview_id}/cancel", headers=other["headers"]).status_code == 404
    assert client.post("/api/interviews/9999/cancel", headers=employer["headers"]).status_code == 404