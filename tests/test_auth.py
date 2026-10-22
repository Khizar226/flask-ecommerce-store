from shop.extensions import db
from shop.models import User


def test_register_hashes_password_and_logs_in(client):
    resp = client.post("/register", data={"email": "New@Example.com ", "password": "long-enough"})
    assert resp.status_code == 302
    user = db.session.scalar(db.select(User).filter_by(email="new@example.com"))
    assert user is not None
    assert user.password_hash != "long-enough"
    assert user.check_password("long-enough")


def test_register_rejects_short_password(client):
    client.post("/register", data={"email": "a@b.co", "password": "short"})
    assert db.session.scalar(db.select(User).filter_by(email="a@b.co")) is None


def test_register_rejects_duplicate_email(client, user):
    resp = client.post("/register", data={"email": user.email, "password": "another-pass"})
    assert resp.headers["Location"].endswith("/login")
    assert db.session.scalar(db.select(db.func.count(User.id))) == 1


def test_login_wrong_password(client, user):
    resp = client.post("/login", data={"email": user.email, "password": "nope-nope"})
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data


def test_login_blocks_open_redirect(client, user):
    resp = client.post(
        "/login?next=https://evil.example.com",
        data={"email": user.email, "password": "correct-horse"},
    )
    assert resp.headers["Location"] == "/"


def test_logout_requires_post(logged_in):
    assert logged_in.get("/logout").status_code == 405
    assert logged_in.post("/logout").status_code == 302
