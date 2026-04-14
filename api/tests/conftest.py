import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch

# Ensure api/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override env vars before importing anything else
_test_uploads = "/tmp/test_uploads"
os.makedirs(_test_uploads, exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-only"
os.environ["UPLOADS_DIR"] = _test_uploads

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Now safe to import main (UPLOADS_DIR will use env var)
import main as _main_module
import routers.admin.items as _admin_items_module
_admin_items_module.UPLOADS_DIR = _test_uploads

from fastapi.testclient import TestClient
from database import Base, get_db
import database as _database_module
from auth.utils import get_password_hash, create_access_token

# Use a single in-memory SQLite DB shared across the test session
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Enable foreign keys on SQLite
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override database module globals so _seed_admin and other direct usages work
_database_module.engine = engine
_database_module.SessionLocal = TestingSessionLocal
_main_module.engine = engine
_main_module.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a DB session for tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app():
    """Create a FastAPI app with DB override and mock static files mount."""
    # We need to patch UPLOADS_DIR before importing main
    os.makedirs("/tmp/test_uploads", exist_ok=True)

    import main as main_module
    main_module.UPLOADS_DIR = "/tmp/test_uploads"

    from main import app as _app
    _app.dependency_overrides[get_db] = _override_get_db
    yield _app
    _app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    """Provide a test client."""
    return TestClient(app, raise_server_exceptions=False)


# ── Helper factories ──────────────────────────────────────────────────────────

@pytest.fixture
def make_admin(db):
    from models import Admin

    def _make(email="admin@test.com", password="admin123", first_name="Admin", last_name="Test"):
        admin = Admin(
            email=email, first_name=first_name, last_name=last_name,
            hashed_password=get_password_hash(password), is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    return _make


@pytest.fixture
def make_customer(db):
    from models import Customer

    def _make(email="cust@test.com", password="cust123", first_name="Jean", last_name="Dupont",
              phone=None, address=None):
        customer = Customer(
            email=email, first_name=first_name, last_name=last_name,
            hashed_password=get_password_hash(password), is_active=True,
            phone=phone, address=address,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer
    return _make


@pytest.fixture
def make_item(db):
    from models import Item

    def _make(title="Widget", price_ht=10.0, tva_rate=20.0, quantity=100, description=None, image_url=None):
        price_ttc = round(price_ht * (1 + tva_rate / 100), 2)
        item = Item(
            title=title, description=description, image_url=image_url,
            price_ht=price_ht, tva_rate=tva_rate, price_ttc=price_ttc, quantity=quantity,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
    return _make


@pytest.fixture
def admin_token():
    """Return a valid admin JWT token."""
    def _make(email="admin@test.com"):
        return create_access_token({"sub": email})
    return _make


@pytest.fixture
def customer_token():
    """Return a valid customer JWT token."""
    def _make(email="cust@test.com"):
        return create_access_token({"sub": email})
    return _make


@pytest.fixture
def auth_admin_client(client, make_admin, admin_token):
    """Client logged in as admin."""
    admin = make_admin()
    token = admin_token(admin.email)
    client.cookies.set("access_token", token)
    return client


@pytest.fixture
def auth_customer_client(client, make_customer, customer_token):
    """Client logged in as customer."""
    customer = make_customer()
    token = customer_token(customer.email)
    client.cookies.set("customer_token", token)
    return client


@pytest.fixture
def cart_cookie():
    """Build a cart cookie value."""
    def _make(cart_dict):
        return json.dumps(cart_dict)
    return _make
