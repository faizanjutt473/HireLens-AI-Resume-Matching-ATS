import pytest

from app import create_app
from app.extensions import db
from config import TestingConfig

from .helpers import fake_embed, unique_email


@pytest.fixture(autouse=True)
def fake_embeddings(monkeypatch):
    monkeypatch.setattr("app.matching.embed", fake_embed)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(TestingConfig, "BCRYPT_LOG_ROUNDS", 4, raising=False)
    app = create_app("testing")
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(client):
    def _make(role, email=None, password="password123"):
        body = {
            "full_name": "Test User",
            "email": email or unique_email(role),
            "password": password,
            "role": role,
        }
        if role == "employer":
            body["company_name"] = "Acme Ltd"
        r = client.post("/api/auth/register", json=body)
        assert r.status_code == 201, r.get_json()
        data = r.get_json()
        return {
            "headers": {"Authorization": "Bearer " + data["access_token"]},
            "refresh": data["refresh_token"],
            "user": data["user"],
            "email": body["email"],
            "password": password,
        }

    return _make


@pytest.fixture()
def employer(make_user):
    return make_user("employer")


@pytest.fixture()
def candidate(make_user):
    return make_user("candidate")


@pytest.fixture()
def sent(monkeypatch):
    """Interview emails ko asli mein bhejne ki jagah list mein jama karta hai."""
    box = []
    monkeypatch.setattr(
        "app.interviews.routes.queue_email", lambda to, subject, body: box.append((to, subject, body))
    )
    return box