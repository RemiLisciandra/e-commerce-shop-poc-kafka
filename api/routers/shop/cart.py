import json
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth.utils import get_current_customer
from database import get_db
from models import Item, Customer

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 jours


def _parse_cart(request: Request) -> dict:
    raw = request.cookies.get("cart", "{}")
    try:
        return {str(k): int(v) for k, v in json.loads(raw).items()}
    except Exception:
        return {}


def _set_cart(response, cart: dict):
    response.set_cookie(
        key="cart",
        value=json.dumps(cart),
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def _get_cart_items(cart: dict, db: Session) -> list[dict]:
    result = []
    for item_id_str, qty in cart.items():
        item = db.query(Item).filter(Item.id == int(item_id_str)).first()
        if item and qty > 0:
            result.append({"item": item, "quantity": qty, "subtotal_ttc": round(item.price_ttc * qty, 2)})
    return result


def _cart_count(cart: dict) -> int:
    return sum(cart.values())


# ── View ──────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def view_cart(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    cart = _parse_cart(request)
    cart_items = _get_cart_items(cart, db)
    total_ttc = round(sum(ci["subtotal_ttc"] for ci in cart_items), 2)
    return templates.TemplateResponse(
        "shop/cart.html",
        {
            "request": request,
            "cart_items": cart_items,
            "total_ttc": total_ttc,
            "customer": current_customer,
            "cart_count": _cart_count(cart),
        },
    )


# ── Add ───────────────────────────────────────────────────────────────────────

@router.post("/add")
def add_to_cart(
    request: Request,
    item_id: int = Form(...),
    quantity: int = Form(1),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == item_id, Item.quantity > 0).first()
    if not item:
        return RedirectResponse(url="/", status_code=302)

    cart = _parse_cart(request)
    current_qty = cart.get(str(item_id), 0)
    max_qty = item.quantity
    cart[str(item_id)] = min(current_qty + max(1, quantity), max_qty)

    response = RedirectResponse(url="/cart", status_code=302)
    _set_cart(response, cart)
    return response


# ── Update ────────────────────────────────────────────────────────────────────

@router.post("/update")
def update_cart(
    request: Request,
    item_id: int = Form(...),
    quantity: int = Form(...),
    db: Session = Depends(get_db),
):
    cart = _parse_cart(request)
    if quantity <= 0:
        cart.pop(str(item_id), None)
    else:
        item = db.query(Item).filter(Item.id == item_id).first()
        if item:
            cart[str(item_id)] = min(quantity, item.quantity)

    response = RedirectResponse(url="/cart", status_code=302)
    _set_cart(response, cart)
    return response


# ── Remove ────────────────────────────────────────────────────────────────────

@router.post("/remove")
def remove_from_cart(request: Request, item_id: int = Form(...)):
    cart = _parse_cart(request)
    cart.pop(str(item_id), None)
    response = RedirectResponse(url="/cart", status_code=302)
    _set_cart(response, cart)
    return response
