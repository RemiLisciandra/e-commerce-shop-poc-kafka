"""Tests for all SQLAlchemy models."""
from datetime import datetime

from models import Admin, Customer, Item, Order, OrderItem, Payment, Invoice
from models.order import OrderStatus
from models.payment import PaymentStatus, PaymentMethod


# ── Admin ─────────────────────────────────────────────────────────────────────

class TestAdminModel:
    def test_create_admin(self, db):
        admin = Admin(
            email="a@b.com", first_name="A", last_name="B",
            hashed_password="hash", is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        assert admin.id is not None
        assert admin.email == "a@b.com"
        assert admin.is_active is True

    def test_admin_defaults(self, db):
        admin = Admin(
            email="x@y.com", first_name="X", last_name="Y",
            hashed_password="hash",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        assert admin.is_active is True


# ── Customer ──────────────────────────────────────────────────────────────────

class TestCustomerModel:
    def test_create_customer(self, db):
        c = Customer(
            email="c@d.com", first_name="C", last_name="D",
            hashed_password="hash", phone="+33600", address="1 rue X",
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        assert c.id is not None
        assert c.phone == "+33600"
        assert c.address == "1 rue X"

    def test_customer_optional_fields(self, db):
        c = Customer(
            email="e@f.com", first_name="E", last_name="F",
            hashed_password="hash",
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        assert c.phone is None
        assert c.address is None

    def test_customer_orders_relationship(self, db):
        c = Customer(email="r@e.com", first_name="R", last_name="E", hashed_password="h")
        db.add(c)
        db.commit()
        db.refresh(c)
        o = Order(customer_id=c.id, total_ht=10.0, total_ttc=12.0)
        db.add(o)
        db.commit()
        db.refresh(c)
        assert len(c.orders) == 1


# ── Item ──────────────────────────────────────────────────────────────────────

class TestItemModel:
    def test_create_item(self, db):
        item = Item(
            title="Gadget", description="Cool", price_ht=10.0,
            tva_rate=20.0, price_ttc=12.0, quantity=50,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        assert item.id is not None
        assert item.price_ttc == 12.0

    def test_item_default_quantity(self, db):
        item = Item(title="T", price_ht=5.0, tva_rate=20.0, price_ttc=6.0)
        db.add(item)
        db.commit()
        db.refresh(item)
        assert item.quantity == 0

    def test_item_image_url(self, db):
        item = Item(title="Img", price_ht=1.0, tva_rate=20.0, price_ttc=1.2, image_url="/uploads/x.jpg")
        db.add(item)
        db.commit()
        db.refresh(item)
        assert item.image_url == "/uploads/x.jpg"


# ── Order & OrderItem ─────────────────────────────────────────────────────────

class TestOrderModel:
    def test_order_status_enum(self):
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.CONFIRMED.value == "confirmed"
        assert OrderStatus.SHIPPED.value == "shipped"
        assert OrderStatus.DELIVERED.value == "delivered"
        assert OrderStatus.CANCELLED.value == "cancelled"

    def test_create_order_with_items(self, db):
        c = Customer(email="o@t.com", first_name="O", last_name="T", hashed_password="h")
        db.add(c)
        db.commit()
        item = Item(title="A", price_ht=10.0, tva_rate=20.0, price_ttc=12.0, quantity=10)
        db.add(item)
        db.commit()
        order = Order(customer_id=c.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.flush()
        oi = OrderItem(order_id=order.id, item_id=item.id, quantity=2,
                       unit_price_ht=10.0, unit_price_ttc=12.0)
        db.add(oi)
        db.commit()
        db.refresh(order)
        assert len(order.items) == 1
        assert order.items[0].quantity == 2

    def test_order_default_status(self, db):
        c = Customer(email="d@d.com", first_name="D", last_name="D", hashed_password="h")
        db.add(c)
        db.commit()
        order = Order(customer_id=c.id, total_ht=0, total_ttc=0)
        db.add(order)
        db.commit()
        db.refresh(order)
        assert order.status == OrderStatus.PENDING


# ── Payment ───────────────────────────────────────────────────────────────────

class TestPaymentModel:
    def test_payment_status_enum(self):
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.COMPLETED.value == "completed"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.REFUNDED.value == "refunded"

    def test_payment_method_enum(self):
        assert PaymentMethod.CARD.value == "card"
        assert PaymentMethod.BANK_TRANSFER.value == "bank_transfer"
        assert PaymentMethod.PAYPAL.value == "paypal"

    def test_create_payment(self, db):
        c = Customer(email="p@t.com", first_name="P", last_name="T", hashed_password="h")
        db.add(c)
        db.commit()
        order = Order(customer_id=c.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.commit()
        pay = Payment(order_id=order.id, amount=12.0, status=PaymentStatus.COMPLETED,
                      payment_method=PaymentMethod.CARD, transaction_id="TXN-123")
        db.add(pay)
        db.commit()
        db.refresh(pay)
        assert pay.id is not None
        assert pay.amount == 12.0

    def test_order_payment_relationship(self, db):
        c = Customer(email="op@t.com", first_name="O", last_name="P", hashed_password="h")
        db.add(c)
        db.commit()
        order = Order(customer_id=c.id, total_ht=5.0, total_ttc=6.0)
        db.add(order)
        db.commit()
        pay = Payment(order_id=order.id, amount=6.0, status=PaymentStatus.COMPLETED,
                      payment_method=PaymentMethod.PAYPAL, transaction_id="TXN-456")
        db.add(pay)
        db.commit()
        db.refresh(order)
        assert order.payment is not None
        assert order.payment.transaction_id == "TXN-456"


# ── Invoice ───────────────────────────────────────────────────────────────────

class TestInvoiceModel:
    def test_create_invoice(self, db):
        c = Customer(email="i@t.com", first_name="I", last_name="T", hashed_password="h")
        db.add(c)
        db.commit()
        order = Order(customer_id=c.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.commit()
        inv = Invoice(
            order_id=order.id, invoice_number="INV-001", total_ht=10.0,
            total_tva=2.0, total_ttc=12.0,
        )
        db.add(inv)
        db.commit()
        db.refresh(inv)
        assert inv.id is not None
        assert inv.invoice_number == "INV-001"

    def test_order_invoice_relationship(self, db):
        c = Customer(email="oi@t.com", first_name="O", last_name="I", hashed_password="h")
        db.add(c)
        db.commit()
        order = Order(customer_id=c.id, total_ht=10.0, total_ttc=12.0)
        db.add(order)
        db.commit()
        inv = Invoice(order_id=order.id, invoice_number="INV-002",
                      total_ht=10.0, total_tva=2.0, total_ttc=12.0)
        db.add(inv)
        db.commit()
        db.refresh(order)
        assert order.invoice is not None
        assert order.invoice.invoice_number == "INV-002"
