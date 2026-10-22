def test_add_update_and_total(client):
    client.post("/cart/add/1")
    client.post("/cart/add/1")
    client.post("/cart/add/2", data={"quantity": 3})
    page = client.get("/cart").data
    assert b"$25.00" in page  # 2 x $12.50
    assert b"$299.97" in page  # 3 x $99.99
    assert b"$324.97" in page  # total

    client.post("/cart/update/2", data={"quantity": 0})
    page = client.get("/cart").data
    assert b"Keyboard" not in page


def test_quantity_is_capped(client):
    client.post("/cart/add/1", data={"quantity": 500})
    with client.session_transaction() as sess:
        assert sess["cart"]["1"] == 20


def test_unknown_product_404(client):
    assert client.post("/cart/add/999").status_code == 404


def test_cart_changes_require_post(client):
    assert client.get("/cart/add/1").status_code == 405
    assert client.get("/cart/clear").status_code == 405


def test_csrf_enforced_when_enabled():
    from shop import create_app
    from shop.config import TestConfig

    class CsrfOn(TestConfig):
        WTF_CSRF_ENABLED = True

    app = create_app(CsrfOn)
    with app.app_context():
        assert app.test_client().post("/cart/clear").status_code == 400
