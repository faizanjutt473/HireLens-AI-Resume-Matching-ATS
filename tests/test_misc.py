import io
from datetime import datetime, timezone

from app.emails import fmt_time, queue_email
from app.extensions import mail
from app.resumes.parser import extract_skills
from app.tasks import send_email

from .helpers import GOOD_RESUME  # noqa: F401


def test_pages_are_served(client):
    assert client.get("/").status_code == 200
    for name in ("login", "register", "jobs", "candidate", "employer"):
        assert client.get(f"/{name}.html").status_code == 200
    assert client.get("/secret.html").status_code == 404


def test_health_endpoint(client):
    assert client.get("/health").get_json() == {"database": "connected", "status": "ok"}


def test_oversized_upload_is_rejected_as_json(client, candidate):
    big = b"%PDF" + b"0" * (6 * 1024 * 1024)
    r = client.post(
        "/api/resumes",
        data={"file": (io.BytesIO(big), "big.pdf")},
        headers=candidate["headers"],
        content_type="multipart/form-data",
    )
    assert r.status_code == 413
    assert "5 MB" in r.get_json()["message"]


def test_email_is_logged_not_sent_when_mail_is_not_configured(app, monkeypatch):
    sent = []
    monkeypatch.setattr(mail, "send", lambda msg: sent.append(msg))
    with app.app_context():
        send_email("a@example.com", "Hello", "Body")
        queue_email("b@example.com", "Hello again", "Body")
    assert sent == []


def test_email_is_sent_when_mail_is_configured(app, monkeypatch):
    sent = []
    monkeypatch.setattr(mail, "send", lambda msg: sent.append(msg))
    app.config["MAIL_SUPPRESS_SEND"] = False
    with app.app_context():
        send_email("a@example.com", "Hello", "Body")
    assert len(sent) == 1
    assert sent[0].recipients == ["a@example.com"] and sent[0].subject == "Hello"


def test_time_is_shown_in_local_timezone(app):
    with app.app_context():
        text = fmt_time(datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc))
    assert "01 December 2026" in text and "03:00 PM" in text  # Asia/Karachi = UTC+5


def test_skill_extraction_uses_aliases_and_keeps_order():
    found = extract_skills("I use Python, scikit learn and k8s daily. Also python again.")
    assert found == ["Python", "scikit-learn", "Kubernetes"]
    assert extract_skills("") == []
    assert extract_skills("Nothing technical in this sentence at all.") == []