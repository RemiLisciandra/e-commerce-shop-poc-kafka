"""Tests for Pydantic schemas."""
from datetime import datetime

from schemas.item import ItemBase, ItemCreate, ItemUpdate, ItemResponse
from schemas.user import UserCreate, UserResponse


class TestItemSchemas:
    def test_item_base(self):
        item = ItemBase(title="T", price_ht=10.0, tva_rate=20.0)
        assert item.title == "T"
        assert item.description is None
        assert item.quantity == 0

    def test_item_create(self):
        item = ItemCreate(title="C", price_ht=5.0)
        assert item.title == "C"
        assert item.tva_rate == 20.0

    def test_item_update(self):
        item = ItemUpdate(title="U", price_ht=8.0, tva_rate=5.5, quantity=10)
        assert item.tva_rate == 5.5

    def test_item_response(self):
        item = ItemResponse(
            id=1, title="R", price_ht=10.0, tva_rate=20.0, price_ttc=12.0,
            created_at=datetime.now(),
        )
        assert item.id == 1
        assert item.price_ttc == 12.0
        assert item.updated_at is None


class TestUserSchemas:
    def test_user_create(self):
        u = UserCreate(email="u@t.com", first_name="F", last_name="L", password="pw")
        assert u.is_admin is False

    def test_user_response(self):
        u = UserResponse(
            id=1, email="u@t.com", first_name="F", last_name="L",
            is_active=True, is_admin=False, created_at=datetime.now(),
        )
        assert u.id == 1
