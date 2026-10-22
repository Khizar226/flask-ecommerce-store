from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import cart
from .extensions import db
from .models import Order, Product

bp = Blueprint("store", __name__)


@bp.route("/")
def home():
    products = db.session.scalars(db.select(Product).filter_by(active=True).order_by(Product.id)).all()
    return render_template("index.html", products=products)


@bp.route("/cart")
def view_cart():
    lines = cart.lines()
    return render_template("cart.html", lines=lines, total_cents=cart.total_cents(lines))


@bp.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id: int):
    product = db.session.get(Product, product_id)
    if not product or not product.active:
        abort(404)
    quantity = request.form.get("quantity", 1, type=int) or 1
    cart.add(product_id, quantity)
    flash(f"Added {product.name} to your cart.", "success")
    return redirect(request.referrer or url_for("store.home"))


@bp.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id: int):
    quantity = request.form.get("quantity", 0, type=int)
    cart.set_quantity(product_id, quantity)
    return redirect(url_for("store.view_cart"))


@bp.route("/cart/clear", methods=["POST"])
def clear_cart():
    cart.clear()
    flash("Your cart is empty.", "info")
    return redirect(url_for("store.view_cart"))


@bp.route("/orders")
@login_required
def orders():
    user_orders = db.session.scalars(
        db.select(Order).filter_by(user_id=current_user.id).order_by(Order.created_at.desc())
    ).all()
    return render_template("orders.html", orders=user_orders)
