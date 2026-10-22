from datetime import UTC, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow():
    return datetime.now(UTC)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    orders = db.relationship("Order", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), default="")
    # Money is stored as integer cents to avoid floating-point rounding errors.
    price_cents = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(500), default="")
    active = db.Column(db.Boolean, default=True, nullable=False)


class Order(db.Model):
    """An order is created as `pending` when checkout starts and marked `paid`
    only after Stripe confirms payment (success redirect or webhook)."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    stripe_session_id = db.Column(db.String(255), unique=True, index=True)
    status = db.Column(db.String(20), default="pending", nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    currency = db.Column(db.String(3), default="usd", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    paid_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", back_populates="orders")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def mark_paid(self) -> bool:
        """Idempotent: returns True only on the first transition to paid."""
        if self.status == "paid":
            return False
        self.status = "paid"
        self.paid_at = utcnow()
        return True


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    # Name and price are snapshotted so later catalog edits don't rewrite history.
    name = db.Column(db.String(120), nullable=False)
    unit_price_cents = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    order = db.relationship("Order", back_populates="items")

    @property
    def line_total_cents(self) -> int:
        return self.unit_price_cents * self.quantity


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
