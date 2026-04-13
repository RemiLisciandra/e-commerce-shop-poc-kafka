from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
from models import Invoice, Item, Order, OrderItem, Payment, User  # noqa: F401 – needed for metadata
from auth.utils import get_password_hash
from routers import auth
from routers.admin import router as admin_router


def _create_tables():
    Base.metadata.create_all(bind=engine)


def _seed_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@shop.com").first():
            db.add(
                User(
                    email="admin@shop.com",
                    first_name="Admin",
                    last_name="Shop",
                    hashed_password=get_password_hash("admin123"),
                    is_admin=True,
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _create_tables()
    _seed_admin()
    yield


app = FastAPI(title="E-Commerce Admin", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(admin_router, prefix="/admin")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login", status_code=302)
