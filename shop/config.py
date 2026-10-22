"""Application configuration, loaded from environment variables.

Secrets never live in source code. Copy `.env.example` to `.env` for local
development; in production set the variables on the host.
"""

import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///shop.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")
    CURRENCY = os.environ.get("STORE_CURRENCY", "usd")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    STRIPE_SECRET_KEY = "sk_test_dummy"
    STRIPE_WEBHOOK_SECRET = "whsec_test_dummy"
