"""Tests for shop auth routes (/login, /register, /logout)."""


class TestCustomerLogin:
    def test_login_page(self, client):
        r = client.get("/login")
        assert r.status_code == 200

    def test_login_page_already_logged_in(self, auth_customer_client):
        r = auth_customer_client.get("/login", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"

    def test_login_success(self, client, make_customer):
        make_customer(email="log@cust.com", password="pw123")
        r = client.post(
            "/login",
            data={"email": "log@cust.com", "password": "pw123", "next": "/"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "customer_token" in r.cookies

    def test_login_custom_next(self, client, make_customer):
        make_customer(email="next@cust.com", password="pw123")
        r = client.post(
            "/login",
            data={"email": "next@cust.com", "password": "pw123", "next": "/checkout"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert r.headers["location"] == "/checkout"

    def test_login_wrong_password(self, client, make_customer):
        make_customer(email="bad@cust.com", password="correct")
        r = client.post("/login", data={"email": "bad@cust.com", "password": "wrong"})
        assert r.status_code == 401

    def test_login_nonexistent(self, client):
        r = client.post("/login", data={"email": "no@x.com", "password": "pw"})
        assert r.status_code == 401

    def test_login_inactive_customer(self, client, db):
        from models import Customer
        from auth.utils import get_password_hash
        c = Customer(email="off@cust.com", first_name="O", last_name="F",
                     hashed_password=get_password_hash("pw"), is_active=False)
        db.add(c)
        db.commit()
        r = client.post("/login", data={"email": "off@cust.com", "password": "pw"})
        assert r.status_code == 401


class TestCustomerRegister:
    def test_register_page(self, client):
        r = client.get("/register")
        assert r.status_code == 200

    def test_register_success(self, client):
        r = client.post(
            "/register",
            data={"email": "new@cust.com", "first_name": "New", "last_name": "User",
                  "password": "pw123", "phone": "", "address": ""},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "customer_token" in r.cookies

    def test_register_with_phone_address(self, client):
        r = client.post(
            "/register",
            data={"email": "full@cust.com", "first_name": "Full", "last_name": "Info",
                  "password": "pw123", "phone": "+33600", "address": "1 rue Test"},
            follow_redirects=False,
        )
        assert r.status_code == 302

    def test_register_duplicate_email(self, client, make_customer):
        make_customer(email="dup@cust.com")
        r = client.post(
            "/register",
            data={"email": "dup@cust.com", "first_name": "D", "last_name": "U",
                  "password": "pw123", "phone": "", "address": ""},
        )
        assert r.status_code == 400


class TestCustomerLogout:
    def test_logout(self, auth_customer_client):
        r = auth_customer_client.get("/logout", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/"
