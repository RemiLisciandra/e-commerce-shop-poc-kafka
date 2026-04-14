"""Tests for cart routes (/cart/*)."""
import json


class TestViewCart:
    def test_empty_cart(self, client):
        r = client.get("/cart")
        assert r.status_code == 200
        assert "vide" in r.text.lower() or "panier" in r.text.lower()

    def test_cart_with_items(self, client, make_item, db):
        item = make_item(title="CartItem", price_ht=10.0, quantity=5)
        client.cookies.set("cart", json.dumps({str(item.id): 2}))
        r = client.get("/cart")
        assert r.status_code == 200
        assert "CartItem" in r.text

    def test_cart_with_invalid_cookie(self, client):
        client.cookies.set("cart", "not-json")
        r = client.get("/cart")
        assert r.status_code == 200  # graceful fallback to empty cart

    def test_cart_with_zero_qty_item(self, client, make_item, db):
        item = make_item(title="ZeroQty")
        client.cookies.set("cart", json.dumps({str(item.id): 0}))
        r = client.get("/cart")
        assert r.status_code == 200


class TestAddToCart:
    def test_add_item(self, client, make_item, db):
        item = make_item(title="AddMe", quantity=10)
        r = client.post(
            "/cart/add",
            data={"item_id": str(item.id), "quantity": "1"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "/cart" in r.headers["location"]

    def test_add_out_of_stock(self, client, make_item, db):
        item = make_item(title="NoStock", quantity=0)
        r = client.post(
            "/cart/add",
            data={"item_id": str(item.id), "quantity": "1"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        # Redirects to home since item not available
        assert r.headers["location"] == "/"

    def test_add_nonexistent_item(self, client):
        r = client.post(
            "/cart/add",
            data={"item_id": "9999", "quantity": "1"},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_add_respects_max_stock(self, client, make_item, db):
        item = make_item(title="Limited", quantity=3)
        # Add 10 but stock is 3
        r = client.post(
            "/cart/add",
            data={"item_id": str(item.id), "quantity": "10"},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_add_increments_existing(self, client, make_item, db):
        item = make_item(title="Incr", quantity=10)
        client.cookies.set("cart", json.dumps({str(item.id): 2}))
        r = client.post(
            "/cart/add",
            data={"item_id": str(item.id), "quantity": "1"},
            follow_redirects=False,
        )
        assert r.status_code == 302


class TestUpdateCart:
    def test_update_quantity(self, client, make_item, db):
        item = make_item(title="Upd", quantity=10)
        client.cookies.set("cart", json.dumps({str(item.id): 2}))
        r = client.post(
            "/cart/update",
            data={"item_id": str(item.id), "quantity": "5"},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_update_to_zero_removes(self, client, make_item, db):
        item = make_item(title="Rem", quantity=10)
        client.cookies.set("cart", json.dumps({str(item.id): 2}))
        r = client.post(
            "/cart/update",
            data={"item_id": str(item.id), "quantity": "0"},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_update_respects_stock(self, client, make_item, db):
        item = make_item(title="MaxS", quantity=3)
        client.cookies.set("cart", json.dumps({str(item.id): 1}))
        r = client.post(
            "/cart/update",
            data={"item_id": str(item.id), "quantity": "100"},
            follow_redirects=False,
        )
        assert r.status_code == 302


class TestRemoveFromCart:
    def test_remove_item(self, client, make_item, db):
        item = make_item(title="Del", quantity=10)
        client.cookies.set("cart", json.dumps({str(item.id): 2}))
        r = client.post(
            "/cart/remove",
            data={"item_id": str(item.id)},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_remove_nonexistent_from_cart(self, client):
        client.cookies.set("cart", json.dumps({"999": 1}))
        r = client.post(
            "/cart/remove",
            data={"item_id": "999"},
            follow_redirects=False,
        )
        assert r.status_code == 302
