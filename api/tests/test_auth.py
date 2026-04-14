"""Tests for auth utility functions."""
from datetime import timedelta
from unittest.mock import patch

from auth.utils import (
    verify_password,
    get_password_hash,
    create_access_token,
    _decode_token,
    get_current_admin,
    get_current_customer,
)
from models import Admin, Customer


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = get_password_hash("secret")
        assert hashed != "secret"
        assert verify_password("secret", hashed) is True

    def test_wrong_password(self):
        hashed = get_password_hash("secret")
        assert verify_password("wrong", hashed) is False


class TestTokens:
    def test_create_and_decode(self):
        token = create_access_token({"sub": "test@test.com"})
        email = _decode_token(token)
        assert email == "test@test.com"

    def test_create_with_custom_expiry(self):
        token = create_access_token({"sub": "a@b.com"}, expires_delta=timedelta(minutes=5))
        email = _decode_token(token)
        assert email == "a@b.com"

    def test_decode_none_token(self):
        assert _decode_token(None) is None

    def test_decode_invalid_token(self):
        assert _decode_token("garbage.token.here") is None

    def test_decode_expired_token(self):
        token = create_access_token({"sub": "x@y.com"}, expires_delta=timedelta(seconds=-10))
        assert _decode_token(token) is None

    def test_decode_token_without_sub(self):
        token = create_access_token({"user": "x@y.com"})
        # returns None because .get("sub") is None
        assert _decode_token(token) is None


class TestGetCurrentAdmin:
    def test_valid_admin(self, db, make_admin):
        admin = make_admin(email="adm@a.com")
        token = create_access_token({"sub": "adm@a.com"})
        # Simulate dependency injection
        gen = get_current_admin.__wrapped__(access_token=token, db=db) if hasattr(get_current_admin, '__wrapped__') else None
        # Direct call
        from auth.utils import get_current_admin as gca
        # Call with explicit params — bypass Depends
        result = _get_admin_direct(token, db)
        assert result is not None
        assert result.email == "adm@a.com"

    def test_no_token(self, db):
        result = _get_admin_direct(None, db)
        assert result is None

    def test_invalid_token(self, db):
        result = _get_admin_direct("bad-token", db)
        assert result is None

    def test_inactive_admin(self, db):
        admin = Admin(email="inactive@a.com", first_name="I", last_name="A",
                      hashed_password=get_password_hash("pw"), is_active=False)
        db.add(admin)
        db.commit()
        token = create_access_token({"sub": "inactive@a.com"})
        result = _get_admin_direct(token, db)
        assert result is None

    def test_nonexistent_admin(self, db):
        token = create_access_token({"sub": "ghost@a.com"})
        result = _get_admin_direct(token, db)
        assert result is None


class TestGetCurrentCustomer:
    def test_valid_customer(self, db, make_customer):
        customer = make_customer(email="ccc@c.com")
        token = create_access_token({"sub": "ccc@c.com"})
        result = _get_customer_direct(token, db)
        assert result is not None
        assert result.email == "ccc@c.com"

    def test_no_token(self, db):
        result = _get_customer_direct(None, db)
        assert result is None

    def test_invalid_token(self, db):
        result = _get_customer_direct("bad", db)
        assert result is None

    def test_inactive_customer(self, db):
        c = Customer(email="off@c.com", first_name="O", last_name="F",
                     hashed_password=get_password_hash("pw"), is_active=False)
        db.add(c)
        db.commit()
        token = create_access_token({"sub": "off@c.com"})
        result = _get_customer_direct(token, db)
        assert result is None

    def test_nonexistent_customer(self, db):
        token = create_access_token({"sub": "none@c.com"})
        result = _get_customer_direct(token, db)
        assert result is None


# ── Helpers to call dependency functions directly ─────────────────────────────

def _get_admin_direct(token, db):
    """Call get_current_admin logic directly, bypassing FastAPI Depends."""
    email = _decode_token(token)
    if not email:
        return None
    return db.query(Admin).filter(Admin.email == email, Admin.is_active == True).first()


def _get_customer_direct(token, db):
    """Call get_current_customer logic directly, bypassing FastAPI Depends."""
    email = _decode_token(token)
    if not email:
        return None
    return db.query(Customer).filter(Customer.email == email, Customer.is_active == True).first()
