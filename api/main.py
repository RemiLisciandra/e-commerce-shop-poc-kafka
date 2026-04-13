from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
from models import Invoice, Item, Order, OrderItem, Payment, Admin, Customer  # noqa: F401
from auth.utils import get_password_hash
from routers import auth
from routers.admin import router as admin_router
from routers.shop import shop_router

UPLOADS_DIR = "/app/uploads"


def _create_tables():
    Base.metadata.create_all(bind=engine)


def _seed_admin():
    db = SessionLocal()
    try:
        if not db.query(Admin).filter(Admin.email == "admin@shop.com").first():
            db.add(
                Admin(
                    email="admin@shop.com",
                    first_name="Admin",
                    last_name="Shop",
                    hashed_password=get_password_hash("admin123"),
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()


os.makedirs(UPLOADS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _create_tables()
    _seed_admin()
    yield


app = FastAPI(title="ShopItem", lifespan=lifespan)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.include_router(auth.router, prefix="/admin")
app.include_router(admin_router, prefix="/admin")
app.include_router(shop_router)
