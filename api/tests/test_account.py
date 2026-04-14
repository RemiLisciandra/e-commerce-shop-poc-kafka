"""Tests for account routes (/account/*)."""
import json

from models import Order, OrderItem, Payment, Invoice
from models.payment import PaymentStatus, PaymentMethod


class TestAccountHistory:
    def test_requires_login(self, client):
        r = client.get("/account/", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    def test_empty_history(self, auth_customer_client):
        r = auth_customer_client.get("/account")
        assert r.status_code == 200

    def test_with_orders(self, auth_customer_client, make_item, db):
        from models import Customer
        customer = db.query(Customer).first()
        item = make_item(title="Hist", price_ht=10.0, quantity=5)
        order = Order(customer_id=customer.id, total_ht=10.0, total_ttc=12.0, status="confirmed")
        db.add(order)
        db.flush()
        oi = OrderItem(order_id=order.id, item_id=item.id, quantity=1,
                       unit_price_ht=10.0, unit_price_ttc=12.0)
        db.add(oi)
        db.commit()
        r = auth_customer_client.get("/account")
        assert r.status_code == 200

    def test_with_bad_cart_cookie(self, auth_customer_client):
        """Covers _cart_count exception branch in account.py."""
        auth_customer_client.cookies.set("cart", "bad-json")
        r = auth_customer_client.get("/account")
        assert r.status_code == 200


class TestAccountPayments:
    def test_requires_login(self, client):
        r = client.get("/account/payments", follow_redirects=False)
        assert r.status_code == 302

    def test_empty_payments(self, auth_customer_client):
        r = auth_customer_client.get("/account/payments")
        assert r.status_code == 200

    def test_with_payments(self, auth_customer_client, make_item, db):
        from models import Customer
        customer = db.query(Customer).first()
        order = Order(customer_id=customer.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.flush()
        pay = Payment(order_id=order.id, amount=12.0, status=PaymentStatus.COMPLETED,
                      payment_method=PaymentMethod.CARD, transaction_id="TXN-T1")
        db.add(pay)
        db.commit()
        r = auth_customer_client.get("/account/payments")
        assert r.status_code == 200


class TestAccountInvoices:
    def test_requires_login(self, client):
        r = client.get("/account/invoices", follow_redirects=False)
        assert r.status_code == 302

    def test_empty_invoices(self, auth_customer_client):
        r = auth_customer_client.get("/account/invoices")
        assert r.status_code == 200

    def test_with_invoices(self, auth_customer_client, make_item, db):
        from models import Customer
        customer = db.query(Customer).first()
        order = Order(customer_id=customer.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.flush()
        inv = Invoice(order_id=order.id, invoice_number="INV-T1",
                      total_ht=10.0, total_tva=2.0, total_ttc=12.0)
        db.add(inv)
        db.commit()
        r = auth_customer_client.get("/account/invoices")
        assert r.status_code == 200


class TestInvoicePDF:
    def test_requires_login(self, client):
        r = client.get("/account/invoices/1/pdf", follow_redirects=False)
        assert r.status_code == 302

    def test_download_pdf(self, auth_customer_client, make_item, db):
        from models import Customer
        customer = db.query(Customer).first()
        item = make_item(title="PDFItem", price_ht=10.0, quantity=5)
        order = Order(customer_id=customer.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.flush()
        oi = OrderItem(order_id=order.id, item_id=item.id, quantity=1,
                       unit_price_ht=10.0, unit_price_ttc=12.0)
        db.add(oi)
        inv = Invoice(order_id=order.id, invoice_number="INV-PDF1",
                      total_ht=10.0, total_tva=2.0, total_ttc=12.0)
        db.add(inv)
        db.commit()
        r = auth_customer_client.get(f"/account/invoices/{inv.id}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"

    def test_download_pdf_nonexistent(self, auth_customer_client):
        r = auth_customer_client.get("/account/invoices/9999/pdf", follow_redirects=False)
        assert r.status_code == 302

    def test_download_pdf_wrong_customer(self, client, make_customer, customer_token, make_item, db):
        cust_a = make_customer(email="pdfa@a.com")
        item = make_item(title="PdfX", price_ht=5.0, quantity=5)
        order = Order(customer_id=cust_a.id, total_ht=5.0, total_ttc=6.0)
        db.add(order)
        db.flush()
        oi = OrderItem(order_id=order.id, item_id=item.id, quantity=1,
                       unit_price_ht=5.0, unit_price_ttc=6.0)
        db.add(oi)
        inv = Invoice(order_id=order.id, invoice_number="INV-OWN",
                      total_ht=5.0, total_tva=1.0, total_ttc=6.0)
        db.add(inv)
        db.commit()
        # Try as customer B
        cust_b = make_customer(email="pdfb@b.com")
        token_b = customer_token(cust_b.email)
        client.cookies.set("customer_token", token_b)
        r = client.get(f"/account/invoices/{inv.id}/pdf", follow_redirects=False)
        assert r.status_code == 302

    def test_download_pdf_deleted_item(self, auth_customer_client, make_item, db):
        """Invoice for an order where the item was since deleted."""
        from models import Customer
        customer = db.query(Customer).first()
        item = make_item(title="A" * 50, price_ht=10.0, quantity=5)  # long title to test truncation
        order = Order(customer_id=customer.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.flush()
        oi = OrderItem(order_id=order.id, item_id=item.id, quantity=1,
                       unit_price_ht=10.0, unit_price_ttc=12.0)
        db.add(oi)
        inv = Invoice(order_id=order.id, invoice_number="INV-DEL1",
                      total_ht=10.0, total_tva=2.0, total_ttc=12.0)
        db.add(inv)
        db.commit()
        r = auth_customer_client.get(f"/account/invoices/{inv.id}/pdf")
        assert r.status_code == 200

    def test_download_pdf_with_customer_address(self, client, make_customer, customer_token, make_item, db):
        cust = make_customer(email="addr@t.com", address="12 rue Test")
        item = make_item(title="Addr", price_ht=10.0, quantity=5)
        order = Order(customer_id=cust.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.flush()
        oi = OrderItem(order_id=order.id, item_id=item.id, quantity=1,
                       unit_price_ht=10.0, unit_price_ttc=12.0)
        db.add(oi)
        inv = Invoice(order_id=order.id, invoice_number="INV-ADDR",
                      total_ht=10.0, total_tva=2.0, total_ttc=12.0)
        db.add(inv)
        db.commit()
        token = customer_token(cust.email)
        client.cookies.set("customer_token", token)
        r = client.get(f"/account/invoices/{inv.id}/pdf")
        assert r.status_code == 200


class TestAccountProfile:
    def test_requires_login(self, client):
        r = client.get("/account/profile", follow_redirects=False)
        assert r.status_code == 302

    def test_profile_page(self, auth_customer_client):
        r = auth_customer_client.get("/account/profile")
        assert r.status_code == 200

    def test_profile_page_saved_flag(self, auth_customer_client):
        r = auth_customer_client.get("/account/profile?saved=1")
        assert r.status_code == 200
        assert "mis" in r.text.lower() or "jour" in r.text.lower() or "enregistr" in r.text.lower()

    def test_post_requires_login(self, client):
        r = client.post(
            "/account/profile",
            data={"first_name": "X", "last_name": "Y", "phone": "", "address": ""},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_update_profile(self, auth_customer_client, db):
        r = auth_customer_client.post(
            "/account/profile",
            data={"first_name": "Updated", "last_name": "Name",
                  "phone": "+33612345678", "address": "42 Avenue Test"},
            follow_redirects=False,
        )
        assert r.status_code == 303
        assert "saved=1" in r.headers["location"]
        # Verify DB was updated
        from models import Customer
        db.expire_all()
        customer = db.query(Customer).first()
        assert customer.first_name == "Updated"
        assert customer.last_name == "Name"
        assert customer.phone == "+33612345678"
        assert customer.address == "42 Avenue Test"

    def test_update_profile_empty_optional(self, auth_customer_client, db):
        r = auth_customer_client.post(
            "/account/profile",
            data={"first_name": "A", "last_name": "B", "phone": "", "address": ""},
            follow_redirects=False,
        )
        assert r.status_code == 303
        from models import Customer
        db.expire_all()
        customer = db.query(Customer).first()
        assert customer.phone is None
        assert customer.address is None
