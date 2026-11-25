from datetime import timedelta

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User


def reg(client, **over):
    body = {
        "full_name": "Ali Khan",
        "email": "ali@example.com",
        "password": "password123",
        "role": "candidate",
        **over,
    }
    return client.post("/api/auth/register", json=body)


def test_register_candidate(client):
    r = reg(client)
    assert r.status_code == 201
    data = r.get_json()
    assert data["user"]["role"] == "candidate"
    assert data["access_token"] and data["refresh_token"]
    assert "password" not in str(data["user"])


def test_register_employer_creates_company(client):
    r = reg(client, role="employer", company_name="Acme Ltd", email="boss@example.com")
    assert r.status_code == 201
    assert r.get_json()["user"]["company"] == "Acme Ltd"


def test_employer_needs_company_name(client):
    assert reg(client, role="employer").status_code == 400


@pytest.mark.parametrize(
    "over",
    [{"email": "not-an-email"}, {"password": "short"}, {"role": "admin"}, {"full_name": ""}],
)
def test_register_validation(client, over):
    assert reg(client, **over).status_code == 400


def test_duplicate_email_rejected(client):
    assert reg(client).status_code == 201
    assert reg(client).status_code == 409


def test_login_works_and_ignores_email_case(client):
    reg(client, email="Ali@Example.com")
    r = client.post("/api/auth/login", json={"email": "ali@example.com", "password": "password123"})
    assert r.status_code == 200
    assert r.get_json()["access_token"]


def test_login_wrong_password_and_unknown_email(client):
    reg(client)
    wrong = client.post("/api/auth/login", json={"email": "ali@example.com", "password": "nope-nope"})
    unknown = client.post("/api/auth/login", json={"email": "x@example.com", "password": "password123"})
    assert wrong.status_code == 401 and unknown.status_code == 401


def test_login_validation(client):
    assert client.post("/api/auth/login", json={"email": "bad"}).status_code == 400


def test_disabled_account_cannot_login(app, client):
    reg(client)
    with app.app_context():
        User.query.filter_by(email="ali@example.com").first().is_active = False
        db.session.commit()
    r = client.post("/api/auth/login", json={"email": "ali@example.com", "password": "password123"})
    assert r.status_code == 403


def test_me_requires_token(client, candidate):
    assert client.get("/api/auth/me").status_code == 401
    r = client.get("/api/auth/me", headers=candidate["headers"])
    assert r.status_code == 200
    assert r.get_json()["user"]["email"] == candidate["email"]


def test_refresh_token_gives_new_access_token(client, candidate):
    r = client.post("/api/auth/refresh", headers={"Authorization": "Bearer " + candidate["refresh"]})
    assert r.status_code == 200
    assert r.get_json()["access_token"]


def test_access_token_cannot_refresh(client, candidate):
    r = client.post("/api/auth/refresh", headers=candidate["headers"])
    assert r.status_code in (401, 422)


def test_role_guard(client, employer, candidate):
    assert client.get("/api/auth/employer-check", headers=employer["headers"]).status_code == 200
    assert client.get("/api/auth/employer-check", headers=candidate["headers"]).status_code == 403
    assert client.get("/api/auth/employer-check").status_code == 401


def test_invalid_and_expired_tokens(app, client):
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401
    with app.app_context():
        old = create_access_token(identity="1", expires_delta=timedelta(seconds=-5))
    expired = client.get("/api/auth/me", headers={"Authorization": "Bearer " + old})
    assert expired.status_code == 401
    assert "expired" in expired.get_json()["message"].lower()