from app.analytics.routes import average, count_skills

from .helpers import apply_new, post_job, set_stage


def test_empty_dashboard(client, employer):
    d = client.get("/api/analytics/employer", headers=employer["headers"]).get_json()
    assert d["summary"]["applicants"] == 0 and d["summary"]["avg_days_to_hire"] is None
    assert [f["count"] for f in d["funnel"]] == [0, 0, 0, 0]
    assert len(d["timeline"]) == 14 and d["per_job"] == []


def test_populated_dashboard(client, make_user, employer):
    j1 = post_job(client, employer, title="Backend Engineer")
    j2 = post_job(client, employer, title="Data Engineer", skills=["Python", "Spark"])
    _, a1 = apply_new(make_user, client, j1["id"])
    _, a2 = apply_new(make_user, client, j1["id"])
    apply_new(make_user, client, j2["id"])

    set_stage(client, employer, a1["id"], "shortlisted")
    set_stage(client, employer, a1["id"], "hired")
    set_stage(client, employer, a2["id"], "rejected")

    other = make_user("employer")
    post_job(client, other, title="DevOps Engineer", skills=["Docker"])

    d = client.get("/api/analytics/employer", headers=employer["headers"]).get_json()
    s = d["summary"]
    assert (s["jobs"], s["open_jobs"], s["applicants"], s["hired"], s["rejected"]) == (2, 2, 3, 1, 1)
    assert s["avg_days_to_hire"] is not None and s["avg_match"] is not None

    counts = [f["count"] for f in d["funnel"]]
    assert counts == [3, 1, 1, 1]
    assert counts == sorted(counts, reverse=True)

    per_job = {j["title"]: j for j in d["per_job"]}
    assert per_job["Backend Engineer"]["applicants"] == 2 and per_job["Backend Engineer"]["hired"] == 1
    assert per_job["Data Engineer"]["applicants"] == 1

    yours = {r["skill"]: r["count"] for r in d["demand_yours"]}
    market = {r["skill"] for r in d["demand_market"]}
    assert yours["Python"] == 2 and yours["Spark"] == 1 and "Docker" not in yours
    assert "Docker" in market
    assert "Python" in {r["skill"] for r in d["applicant_skills"]}
    assert sum(t["count"] for t in d["timeline"]) == 3


def test_candidate_cannot_see_analytics(client, candidate):
    assert client.get("/api/analytics/employer", headers=candidate["headers"]).status_code == 403
    assert client.get("/api/analytics/employer").status_code == 401


def test_count_skills_counts_once_per_job_and_ignores_case():
    rows = count_skills([["Python", "python"], ["python", "Flask"], [], None])
    assert rows[0] == {"skill": "Python", "count": 2}
    assert {"skill": "Flask", "count": 1} in rows


def test_average():
    assert average([]) is None
    assert average([1, 2]) == 1.5