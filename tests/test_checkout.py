from unittest.mock import patch

import stripe

from shop.extensions import db
from shop.models import Order


def stripe_obj(data):
    return stripe.StripeObject.construct_from(data, "sk_test_dummy")


def start_checkout(client):
    client.post("/cart/add/1", data={"quantity": 2})
    fake = stripe_obj({"id": "cs_test_123", "url": "https://checkout.stripe.com/pay/cs_test_123"})
    with patch("stripe.checkout.Session.create", return_value=fake) as create:
        resp = client.post("/checkout")
    return resp, create


def test_checkout_requires_login(client):
    client.post("/cart/add/1")
    resp = client.post("/checkout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_checkout_creates_pending_order_with_db_prices(logged_in, user):
    resp, create = start_checkout(logged_in)
    assert resp.status_code == 303
    assert resp.headers["Location"].startswith("https://checkout.stripe.com/")

    kwargs = create.call_args.kwargs
    assert kwargs["line_items"][0]["price_data"]["unit_amount"] == 1250
    assert kwargs["line_items"][0]["quantity"] == 2
    assert kwargs["client_reference_id"] == str(user.id)
    assert "{CHECKOUT_SESSION_ID}" in kwargs["success_url"]

    order = db.session.scalar(db.select(Order))
    assert order.status == "pending"
    assert order.total_cents == 2500
    assert order.stripe_session_id == "cs_test_123"


def test_stripe_error_rolls_back(logged_in):
    logged_in.post("/cart/add/1")
    with patch("stripe.checkout.Session.create", side_effect=stripe.APIConnectionError("down")):
        resp = logged_in.post("/checkout")
    assert resp.headers["Location"].endswith("/cart")
    assert db.session.scalar(db.select(Order)) is None


def test_success_marks_paid_only_when_stripe_confirms(logged_in, user):
    start_checkout(logged_in)
    unpaid = stripe_obj(
        {"id": "cs_test_123", "payment_status": "unpaid", "client_reference_id": str(user.id)}
    )
    with patch("stripe.checkout.Session.retrieve", return_value=unpaid):
        logged_in.get("/checkout/success?session_id=cs_test_123")
    assert db.session.scalar(db.select(Order)).status == "pending"

    paid = stripe_obj({"id": "cs_test_123", "payment_status": "paid", "client_reference_id": str(user.id)})
    with patch("stripe.checkout.Session.retrieve", return_value=paid):
        resp = logged_in.get("/checkout/success?session_id=cs_test_123")
        logged_in.get("/checkout/success?session_id=cs_test_123")  # idempotent replay
    assert resp.status_code == 200
    order = db.session.scalar(db.select(Order))
    assert order.status == "paid"
    with logged_in.session_transaction() as sess:
        assert "cart" not in sess


def test_success_rejects_someone_elses_session(logged_in):
    start_checkout(logged_in)
    other = stripe_obj({"id": "cs_test_123", "payment_status": "paid", "client_reference_id": "999"})
    with patch("stripe.checkout.Session.retrieve", return_value=other):
        resp = logged_in.get("/checkout/success?session_id=cs_test_123")
    assert resp.status_code == 403


def test_success_without_session_id_is_rejected(logged_in):
    assert logged_in.get("/checkout/success").status_code == 400


def test_webhook_rejects_bad_signature(client):
    resp = client.post("/stripe/webhook", data=b"{}", headers={"Stripe-Signature": "t=1,v1=bad"})
    assert resp.status_code == 400


def test_webhook_fulfils_order(logged_in, client):
    start_checkout(logged_in)
    event = stripe_obj(
        {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test_123", "object": "checkout.session", "payment_status": "paid"}},
        }
    )
    with patch("stripe.Webhook.construct_event", return_value=event):
        resp = client.post("/stripe/webhook", data=b"{}", headers={"Stripe-Signature": "ok"})
    assert resp.status_code == 200
    assert db.session.scalar(db.select(Order)).status == "paid"
