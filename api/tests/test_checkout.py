"""Tests for checkout/orders routes (/checkout/*)."""
import json


class TestCheckoutPage:
    def test_checkout_requires_login(self, client):
        client.cookies.set("cart", json.dumps({"1": 1}))
        r = client.get("/checkout/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    def test_checkout_empty_cart(self, auth_customer_client):
        r = auth_customer_client.get("/checkout/", follow_redirects=False)
        assert r.status_code == 302
        assert "/cart" in r.headers["location"]

    def test_checkout_bad_cart_cookie(self, auth_customer_client):
        """Covers _parse_cart exception branch in orders.py."""
        auth_customer_client.cookies.set("cart", "bad-json")
        r = auth_customer_client.get("/checkout/", follow_redirects=False)
        assert r.status_code == 302  # empty cart -> redirect

    def test_checkout_page(self, auth_customer_client, make_item, db):
        item = make_item(title="CheckItem", price_ht=10.0, quantity=5)
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 2}))
        r = auth_customer_client.get("/checkout")
        assert r.status_code == 200
        assert "CheckItem" in r.text

    def test_checkout_skip_invalid_items(self, auth_customer_client, make_item, db):
        item = make_item(title="Valid", price_ht=5.0, quantity=3)
        # Cart contains a valid item and a nonexistent one
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 1, "9999": 2}))
        r = auth_customer_client.get("/checkout")
        assert r.status_code == 200
        assert "Valid" in r.text


class TestConfirmOrder:
    def test_confirm_requires_login(self, client):
        client.cookies.set("cart", json.dumps({"1": 1}))
        r = client.post("/checkout/confirm", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    def test_confirm_empty_cart(self, auth_customer_client):
        r = auth_customer_client.post("/checkout/confirm", follow_redirects=False)
        assert r.status_code == 302
        assert "/cart" in r.headers["location"]

    def test_confirm_success(self, auth_customer_client, make_item, db):
        item = make_item(title="OrderMe", price_ht=10.0, tva_rate=20.0, quantity=10)
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 2}))
        r = auth_customer_client.post("/checkout/confirm", follow_redirects=False)
        assert r.status_code == 302
        assert "/checkout/" in r.headers["location"]
        assert "/confirmation" in r.headers["location"]

    def test_confirm_decrements_stock(self, auth_customer_client, make_item, db):
        item = make_item(title="Stock", price_ht=5.0, quantity=10)
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 3}))
        auth_customer_client.post("/checkout/confirm", follow_redirects=False)
        db.expire_all()
        from models import Item
        updated = db.query(Item).filter(Item.id == item.id).first()
        assert updated.quantity == 7

    def test_confirm_creates_payment_and_invoice(self, auth_customer_client, make_item, db):
        item = make_item(title="Full", price_ht=20.0, quantity=5)
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 1}))
        auth_customer_client.post("/checkout/confirm", follow_redirects=False)
        from models import Order, Payment, Invoice
        order = db.query(Order).first()
        assert order is not None
        assert order.status.value == "confirmed" or order.status == "confirmed"
        payment = db.query(Payment).filter(Payment.order_id == order.id).first()
        assert payment is not None
        assert payment.amount == order.total_ttc
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
        assert invoice is not None
        assert invoice.invoice_number.startswith("INV-")

    def test_confirm_skips_invalid_items(self, auth_customer_client, make_item, db):
        item = make_item(title="ValidOnly", price_ht=10.0, quantity=5)
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 1, "9999": 3}))
        r = auth_customer_client.post("/checkout/confirm", follow_redirects=False)
        assert r.status_code == 302

    def test_confirm_qty_capped_to_stock(self, auth_customer_client, make_item, db):
        item = make_item(title="Limited", price_ht=10.0, quantity=2)
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 10}))
        auth_customer_client.post("/checkout/confirm", follow_redirects=False)
        db.expire_all()
        from models import Item
        updated = db.query(Item).filter(Item.id == item.id).first()
        assert updated.quantity == 0


class TestOrderConfirmation:
    def test_confirmation_requires_login(self, client):
        r = client.get("/checkout/1/confirmation", follow_redirects=False)
        assert r.status_code == 302

    def test_confirmation_page(self, auth_customer_client, make_item, db):
        # Create an order first
        item = make_item(title="Confirmed", price_ht=10.0, quantity=10)
        auth_customer_client.cookies.set("cart", json.dumps({str(item.id): 1}))
        r = auth_customer_client.post("/checkout/confirm", follow_redirects=False)
        location = r.headers["location"]
        r2 = auth_customer_client.get(location)
        assert r2.status_code == 200

    def test_confirmation_wrong_customer(self, client, make_customer, customer_token, make_item, db):
        # Create order with customer A
        cust_a = make_customer(email="a@a.com")
        item = make_item(title="X", price_ht=5.0, quantity=5)
        token_a = customer_token(cust_a.email)
        client.cookies.set("customer_token", token_a)
        client.cookies.set("cart", json.dumps({str(item.id): 1}))
        r = client.post("/checkout/confirm", follow_redirects=False)
        location = r.headers["location"]
        # Now try to access as customer B
        cust_b = make_customer(email="b@b.com")
        token_b = customer_token(cust_b.email)
        client.cookies.set("customer_token", token_b)
        r2 = client.get(location, follow_redirects=False)
        assert r2.status_code == 302  # redirect to /

    def test_confirmation_nonexistent_order(self, auth_customer_client):
        r = auth_customer_client.get("/checkout/9999/confirmation", follow_redirects=False)
        assert r.status_code == 302
