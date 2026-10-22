"""Session-backed cart.

The session only stores product ids and quantities; prices are always read
from the database, so a client can never change what it pays.
"""

from dataclasses import dataclass

from flask import session

from .extensions import db
from .models import Product

MAX_QTY = 20
_KEY = "cart"


@dataclass
class CartLine:
    product: Product
    quantity: int

    @property
    def total_cents(self) -> int:
        return self.product.price_cents * self.quantity


def _raw() -> dict[str, int]:
    data = session.get(_KEY, {})
    return data if isinstance(data, dict) else {}


def _save(data: dict[str, int]) -> None:
    session[_KEY] = data
    session.modified = True


def add(product_id: int, quantity: int = 1) -> None:
    data = _raw()
    key = str(product_id)
    data[key] = min(data.get(key, 0) + max(quantity, 1), MAX_QTY)
    _save(data)


def set_quantity(product_id: int, quantity: int) -> None:
    data = _raw()
    key = str(product_id)
    if quantity <= 0:
        data.pop(key, None)
    else:
        data[key] = min(quantity, MAX_QTY)
    _save(data)


def clear() -> None:
    session.pop(_KEY, None)


def count() -> int:
    return sum(_raw().values())


def lines() -> list[CartLine]:
    result = []
    for key, qty in _raw().items():
        product = db.session.get(Product, int(key))
        if product and product.active and qty > 0:
            result.append(CartLine(product, qty))
    return result


def total_cents(cart_lines: list[CartLine]) -> int:
    return sum(line.total_cents for line in cart_lines)
