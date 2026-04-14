from fastapi import APIRouter

from .catalog import router as catalog_router
from .cart import router as cart_router
from .orders import router as orders_router
from .auth import router as auth_router
from .account import router as account_router

shop_router = APIRouter()
shop_router.include_router(auth_router)
shop_router.include_router(catalog_router)
shop_router.include_router(cart_router, prefix="/cart")
shop_router.include_router(orders_router, prefix="/orders")
shop_router.include_router(account_router, prefix="/account")
