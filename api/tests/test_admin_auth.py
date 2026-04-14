"""Tests for admin auth router (/admin/login, /admin/logout)."""


class TestAdminLogin:
    def test_login_page(self, client):
        r = client.get("/admin/login")
        assert r.status_code == 200
        assert "login" in r.text.lower() or "mot de passe" in r.text.lower()

    def test_login_page_already_logged_in(self, auth_admin_client):
        r = auth_admin_client.get("/admin/login", follow_redirects=False)
        assert r.status_code == 302
        assert "/admin/items" in r.headers["location"]

    def test_login_success(self, client, make_admin):
        make_admin(email="log@admin.com", password="pw123")
        r = client.post(
            "/admin/login",
            data={"email": "log@admin.com", "password": "pw123"},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "access_token" in r.cookies

    def test_login_wrong_password(self, client, make_admin):
        make_admin(email="bad@admin.com", password="correct")
        r = client.post(
            "/admin/login",
            data={"email": "bad@admin.com", "password": "wrong"},
        )
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = client.post(
            "/admin/login",
            data={"email": "no@admin.com", "password": "pw"},
        )
        assert r.status_code == 401


class TestAdminLogout:
    def test_logout(self, auth_admin_client):
        r = auth_admin_client.get("/admin/logout", follow_redirects=False)
        assert r.status_code == 302
        assert "/admin/login" in r.headers["location"]
