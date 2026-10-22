"""Stripe Checkout flow.

1. POST /checkout          -> snapshot the cart into a `pending` Order and
                              redirect to a Stripe-hosted payment page.
2. GET  /checkout/success  -> verify the session with Stripe's API, then mark
                              the order `paid`. The URL alone proves nothing.
3. POST /stripe/webhook    -> signature-verified backup path, so orders are
                              fulfilled even if the browser never returns.
"""

import logging

import stripe
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import cart
from .extensions import csrf, db
from .models import Order, OrderItem

bp = Blueprint("checkout", __name__)
log = logging.getLogger(__name__)


def _stripe_ready() -> bool:
    key = current_app.config["STRIPE_SECRET_KEY"]
    stripe.api_key = key
    return bool(key)


def _fulfil(session_obj) -> Order | None:
    """Mark the matching order paid. Safe to call more than once."""
    if getattr(session_obj, "payment_status", None) != "paid":
        return None
    order = db.session.scalar(db.select(Order).filter_by(stripe_session_id=session_obj.id))
    if order is None:
        log.warning("Paid Stripe session %s has no matching order", session_obj.id)
        return None
    if order.mark_paid():
        db.session.commit()
    return order


@bp.route("/checkout", methods=["POST"])
@login_required
def create_checkout_session():
    lines = cart.lines()
    if not lines:
        flash("Your cart is empty.", "info")
        return redirect(url_for("store.view_cart"))
    if not _stripe_ready():
        flash("Payments are not configured. Set STRIPE_SECRET_KEY to enable checkout.", "warning")
        return redirect(url_for("store.view_cart"))

    currency = current_app.config["CURRENCY"]
    order = Order(user_id=current_user.id, total_cents=cart.total_cents(lines), currency=currency)
    for line in lines:
        order.items.append(
            OrderItem(
                product_id=line.product.id,
                name=line.product.name,
                unit_price_cents=line.product.price_cents,
                quantity=line.quantity,
            )
        )
    db.session.add(order)
    db.session.flush()  # assigns order.id

    base = current_app.config["BASE_URL"]
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            client_reference_id=str(current_user.id),
            customer_email=current_user.email,
            metadata={"order_id": str(order.id)},
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {"name": item.name},
                        "unit_amount": item.unit_price_cents,
                    },
                    "quantity": item.quantity,
                }
                for item in order.items
            ],
            success_url=f"{base}{url_for('checkout.success')}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}{url_for('checkout.cancel')}",
        )
    except stripe.StripeError:
        db.session.rollback()
        log.exception("Stripe checkout session creation failed")
        flash("We couldn't start the payment. Please try again.", "danger")
        return redirect(url_for("store.view_cart"))

    order.stripe_session_id = checkout_session.id
    db.session.commit()
    return redirect(checkout_session.url, code=303)


@bp.route("/checkout/success")
@login_required
def success():
    session_id = request.args.get("session_id", "")
    if not session_id or not _stripe_ready():
        abort(400)
    try:
        session_obj = stripe.checkout.Session.retrieve(session_id)
    except stripe.StripeError:
        log.exception("Could not retrieve Stripe session %s", session_id)
        abort(400)

    if getattr(session_obj, "client_reference_id", None) != str(current_user.id):
        abort(403)

    order = _fulfil(session_obj)
    if order is None:
        flash("Your payment hasn't been confirmed yet. We'll update your order shortly.", "warning")
        return redirect(url_for("store.orders"))

    cart.clear()
    return render_template("success.html", order=order)


@bp.route("/checkout/cancel")
def cancel():
    flash("Checkout cancelled. Your cart is still here.", "info")
    return redirect(url_for("store.view_cart"))


@bp.route("/stripe/webhook", methods=["POST"])
@csrf.exempt
def webhook():
    secret = current_app.config["STRIPE_WEBHOOK_SECRET"]
    if not secret:
        abort(404)
    try:
        event = stripe.Webhook.construct_event(
            request.get_data(), request.headers.get("Stripe-Signature", ""), secret
        )
    except (ValueError, stripe.SignatureVerificationError):
        abort(400)

    if event.type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        _fulfil(event.data.object)
    return "", 200
