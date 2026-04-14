"""Tests for main.py (lifespan, seed admin, app setup)."""
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient
import asyncio


class TestMainApp:
    def test_app_exists(self, app):
        from main import app as the_app
        assert the_app is not None
        assert the_app.title == "ShopItem"

    def test_seed_admin_creates_admin(self, db):
        """_seed_admin uses SessionLocal (now overridden to test engine)."""
        from main import _seed_admin
        _seed_admin()
        from models import Admin
        db.expire_all()
        admin = db.query(Admin).filter(Admin.email == "admin@shop.com").first()
        assert admin is not None
        assert admin.first_name == "Admin"

    def test_seed_admin_idempotent(self, db):
        from main import _seed_admin
        _seed_admin()
        _seed_admin()  # should not raise or create duplicate
        from models import Admin
        count = db.query(Admin).filter(Admin.email == "admin@shop.com").count()
        assert count == 1

    def test_create_tables(self):
        from main import _create_tables
        _create_tables()  # should not raise

    def test_routes_registered(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_lifespan(self, app):
        """Test that lifespan runs (tables created + admin seeded)."""
        # TestClient.__enter__ triggers the lifespan
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/")
            assert r.status_code == 200
