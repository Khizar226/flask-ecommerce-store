import logging

import click
from flask import Flask

from . import cart
from .config import Config
from .extensions import csrf, db, login_manager
from .models import Product

SAMPLE_PRODUCTS = [
    (
        "Python T-Shirt",
        "Soft cotton tee for your favourite language.",
        2500,
        "/static/img/tshirt.svg",
    ),
    (
        "Flask Coffee Mug",
        "Holds enough coffee for one long debugging session.",
        1250,
        "/static/img/mug.svg",
    ),
    (
        "Mechanical Keyboard",
        "Tactile switches, aluminium frame, zero regrets.",
        9999,
        "/static/img/keyboard.svg",
    ),
]


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is not set. Copy .env.example to .env and generate one with:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"'
        )

    logging.basicConfig(level=logging.INFO)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import auth, checkout, store

    app.register_blueprint(store.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(checkout.bp)

    @app.context_processor
    def inject_globals():
        return {"cart_count": cart.count()}

    @app.template_filter("money")
    def money(cents: int) -> str:
        return f"${cents / 100:,.2f}"

    @app.cli.command("seed")
    def seed():
        """Add sample products if the catalog is empty."""
        if db.session.scalar(db.select(Product).limit(1)):
            click.echo("Catalog already has products; nothing to do.")
            return
        for name, desc, price, image in SAMPLE_PRODUCTS:
            db.session.add(Product(name=name, description=desc, price_cents=price, image_url=image))
        db.session.commit()
        click.echo(f"Added {len(SAMPLE_PRODUCTS)} sample products.")

    with app.app_context():
        db.create_all()

    return app
