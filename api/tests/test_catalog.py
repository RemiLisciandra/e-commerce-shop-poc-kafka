"""Tests for catalog route (/)."""


class TestCatalog:
    def test_catalog_anonymous(self, client, make_item, db):
        make_item(title="Product A", quantity=10)
        make_item(title="Product B", quantity=0)  # out of stock
        r = client.get("/")
        assert r.status_code == 200
        assert "Product A" in r.text
        # Out of stock items should NOT appear
        assert "Product B" not in r.text

    def test_catalog_logged_in(self, auth_customer_client, make_item, db):
        make_item(title="In Stock")
        r = auth_customer_client.get("/")
        assert r.status_code == 200
        assert "In Stock" in r.text

    def test_catalog_reorder_items(self, auth_customer_client, make_item, make_customer, db):
        """Customer who has ordered before sees reorder suggestions."""
        from models import Order, OrderItem
        # Create item
        item = make_item(title="Reorder Me", quantity=50)
        # Get the customer (created by auth_customer_client fixture)
        from models import Customer
        customer = db.query(Customer).first()
        # Create a past order
        order = Order(customer_id=customer.id, total_ht=10.0, total_ttc=12.0, status="confirmed")
        db.add(order)
        db.flush()
        oi = OrderItem(order_id=order.id, item_id=item.id, quantity=1,
                       unit_price_ht=10.0, unit_price_ttc=12.0)
        db.add(oi)
        db.commit()
        r = auth_customer_client.get("/")
        assert r.status_code == 200

    def test_catalog_empty(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_catalog_with_bad_cart_cookie(self, client):
        """Covers _cart_count exception branch."""
        client.cookies.set("cart", "not-json")
        r = client.get("/")
        assert r.status_code == 200
