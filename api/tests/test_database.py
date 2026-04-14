"""Tests for database module."""
from database import get_db, SessionLocal, Base, engine


class TestDatabase:
    def test_get_db_yields_session(self):
        gen = get_db()
        session = next(gen)
        assert session is not None
        try:
            next(gen)
        except StopIteration:
            pass

    def test_base_has_metadata(self):
        assert hasattr(Base, "metadata")
