import os

from .helpers import BAD_RESUME, GOOD_RESUME, docx_bytes, pdf_bytes, upload


def test_upload_docx_extracts_skills(client, candidate):
    r = upload(client, candidate["headers"], docx_bytes(GOOD_RESUME))
    assert r.status_code == 201
    resume = r.get_json()["resume"]
    assert resume["is_active"] is True
    assert {"Python", "Flask", "PostgreSQL", "Docker"} <= set(resume["skills"])


def test_upload_pdf(client, candidate):
    lines = [
        "Backend developer with five years of experience.",
        "Skills: Python, Flask, PostgreSQL, Docker and Redis.",
    ]
    r = upload(client, candidate["headers"], pdf_bytes(lines), name="cv.pdf")
    assert r.status_code == 201, r.get_json()
    assert {"Python", "Flask", "PostgreSQL"} <= set(r.get_json()["resume"]["skills"])


def test_rejects_bad_uploads(client, candidate):
    h = candidate["headers"]
    assert client.post("/api/resumes", headers=h).status_code == 400
    assert upload(client, h, b"hello", name="notes.txt").status_code == 400
    assert upload(client, h, b"not really a pdf" * 10, name="fake.pdf").status_code == 400
    assert upload(client, h, docx_bytes("Hi"), name="short.docx").status_code == 422
    assert upload(client, h, b"PK\x03\x04garbage", name="broken.docx").status_code == 422


def test_rejected_upload_leaves_no_file(app, client, candidate):
    upload(client, candidate["headers"], docx_bytes("Hi"), name="short.docx")
    assert os.listdir(app.config["UPLOAD_FOLDER"]) == []


def test_employer_cannot_upload(client, employer):
    assert upload(client, employer["headers"], docx_bytes(GOOD_RESUME)).status_code == 403


def test_list_and_switch_active_resume(client, candidate):
    h = candidate["headers"]
    first = upload(client, h, docx_bytes(GOOD_RESUME)).get_json()["resume"]
    second = upload(client, h, docx_bytes(BAD_RESUME)).get_json()["resume"]
    items = client.get("/api/resumes", headers=h).get_json()["resumes"]
    assert len(items) == 2
    assert {r["id"]: r["is_active"] for r in items} == {first["id"]: False, second["id"]: True}

    r = client.patch(f"/api/resumes/{first['id']}", json={"is_active": True}, headers=h)
    assert r.status_code == 200
    items = client.get("/api/resumes", headers=h).get_json()["resumes"]
    assert {r["id"]: r["is_active"] for r in items} == {first["id"]: True, second["id"]: False}


def test_edit_skills(client, candidate):
    h = candidate["headers"]
    resume = upload(client, h, docx_bytes(GOOD_RESUME)).get_json()["resume"]
    r = client.patch(f"/api/resumes/{resume['id']}", json={"skills": ["Go", "go", "Rust"]}, headers=h)
    assert r.get_json()["resume"]["skills"] == ["Go", "Rust"]
    assert client.patch(f"/api/resumes/{resume['id']}", json={"is_active": False}, headers=h).status_code == 400


def test_delete_active_resume_promotes_previous(app, client, candidate):
    h = candidate["headers"]
    first = upload(client, h, docx_bytes(GOOD_RESUME)).get_json()["resume"]
    second = upload(client, h, docx_bytes(BAD_RESUME)).get_json()["resume"]
    assert len(os.listdir(app.config["UPLOAD_FOLDER"])) == 2

    assert client.delete(f"/api/resumes/{second['id']}", headers=h).status_code == 200
    items = client.get("/api/resumes", headers=h).get_json()["resumes"]
    assert len(items) == 1 and items[0]["id"] == first["id"] and items[0]["is_active"] is True
    assert len(os.listdir(app.config["UPLOAD_FOLDER"])) == 1


def test_cannot_touch_someone_elses_resume(client, make_user, candidate):
    resume = upload(client, candidate["headers"], docx_bytes(GOOD_RESUME)).get_json()["resume"]
    other = make_user("candidate")
    assert client.patch(f"/api/resumes/{resume['id']}", json={"skills": ["x"]}, headers=other["headers"]).status_code == 404
    assert client.delete(f"/api/resumes/{resume['id']}", headers=other["headers"]).status_code == 404


def test_resume_limit(client, candidate):
    for _ in range(5):
        assert upload(client, candidate["headers"], docx_bytes(GOOD_RESUME)).status_code == 201
    r = upload(client, candidate["headers"], docx_bytes(GOOD_RESUME))
    assert r.status_code == 400
    assert "5" in r.get_json()["message"]