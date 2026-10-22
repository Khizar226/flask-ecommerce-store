import pytest

from shop import create_app
from shop.config import TestConfig
from shop.extensions import db
from shop.models import Product, User


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.session.add_all(
            [
                Product(name="Mug", description="", price_cents=1250),
                Product(name="Keyboard", description="", price_cents=9999),
            ]
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(email="buyer@example.com")
    u.set_password("correct-horse")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def logged_in(client, user):
    client.post("/login", data={"email": user.email, "password": "correct-horse"})
    return client
