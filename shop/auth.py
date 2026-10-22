import re
from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import User

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8


def _safe_next(target: str | None) -> str:
    """Only allow relative redirects, blocking open-redirect attacks."""
    if target and not urlsplit(target).netloc and target.startswith("/"):
        return target
    return url_for("store.home")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("store.home"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not EMAIL_RE.match(email):
            flash("Enter a valid email address.", "danger")
        elif len(password) < MIN_PASSWORD:
            flash(f"Password must be at least {MIN_PASSWORD} characters.", "danger")
        elif db.session.scalar(db.select(User).filter_by(email=email)):
            flash("That email is already registered. Please log in.", "warning")
            return redirect(url_for("auth.login"))
        else:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created. Welcome!", "success")
            return redirect(url_for("store.home"))
    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("store.home"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = db.session.scalar(db.select(User).filter_by(email=email))
        if user and user.check_password(password):
            login_user(user)
            return redirect(_safe_next(request.args.get("next")))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("store.home"))
