import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth.utils import get_current_customer
from database import get_db
from models import Item, Customer, Order, OrderItem

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _parse_cart(request: Request) -> dict:
    raw = request.cookies.get("cart", "{}")
    try:
        return {str(k): int(v) for k, v in json.loads(raw).items()}
    except Exception:
        return {}


def _cart_count(cart: dict) -> int:
    return sum(cart.values())


# ── Checkout summary ──────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def checkout_page(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    if not current_customer:
        return RedirectResponse(url="/login?next=/checkout", status_code=302)

    cart = _parse_cart(request)
    if not cart:
        return RedirectResponse(url="/cart", status_code=302)

    cart_items = []
    total_ht = 0.0
    total_ttc = 0.0
    for item_id_str, qty in cart.items():
        item = db.query(Item).filter(Item.id == int(item_id_str)).first()
        if item and qty > 0:
            subtotal_ht = round(item.price_ht * qty, 2)
            subtotal_ttc = round(item.price_ttc * qty, 2)
            cart_items.append({"item": item, "quantity": qty, "subtotal_ht": subtotal_ht, "subtotal_ttc": subtotal_ttc})
            total_ht += subtotal_ht
            total_ttc += subtotal_ttc

    return templates.TemplateResponse(
        "shop/checkout.html",
        {
            "request": request,
            "cart_items": cart_items,
            "total_ht": round(total_ht, 2),
            "total_ttc": round(total_ttc, 2),
            "customer": current_customer,
            "cart_count": _cart_count(cart),
        },
    )


# ── Confirm order ─────────────────────────────────────────────────────────────

@router.post("/confirm")
def confirm_order(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    if not current_customer:
        return RedirectResponse(url="/login?next=/checkout", status_code=302)

    cart = _parse_cart(request)
    if not cart:
        return RedirectResponse(url="/cart", status_code=302)

    total_ht = 0.0
    total_ttc = 0.0
    order_items_data = []

    for item_id_str, qty in cart.items():
        item = db.query(Item).filter(Item.id == int(item_id_str)).first()
        if not item or qty <= 0:
            continue
        actual_qty = min(qty, item.quantity)
        subtotal_ht = round(item.price_ht * actual_qty, 2)
        subtotal_ttc = round(item.price_ttc * actual_qty, 2)
        total_ht += subtotal_ht
        total_ttc += subtotal_ttc
        order_items_data.append((item, actual_qty))
        item.quantity -= actual_qty  # decrement stock

    order = Order(
        customer_id=current_customer.id,
        total_ht=round(total_ht, 2),
        total_ttc=round(total_ttc, 2),
    )
    db.add(order)
    db.flush()  # get order.id

    for item, qty in order_items_data:
        db.add(OrderItem(
            order_id=order.id,
            item_id=item.id,
            quantity=qty,
            unit_price_ht=item.price_ht,
            unit_price_ttc=item.price_ttc,
        ))

    db.commit()

    response = RedirectResponse(url=f"/orders/{order.id}/confirmation", status_code=302)
    response.delete_cookie("cart")
    return response


# ── Confirmation ──────────────────────────────────────────────────────────────

@router.get("/{order_id}/confirmation", response_class=HTMLResponse)
def order_confirmation(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    if not current_customer:
        return RedirectResponse(url="/login", status_code=302)

    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.customer_id == current_customer.id)
        .first()
    )
    if not order:
        return RedirectResponse(url="/", status_code=302)

    order_items = []
    for oi in order.items:
        order_items.append({"item": oi.item, "quantity": oi.quantity, "subtotal_ttc": round(oi.unit_price_ttc * oi.quantity, 2)})

    return templates.TemplateResponse(
        "shop/confirmation.html",
        {
            "request": request,
            "order": order,
            "order_items": order_items,
            "customer": current_customer,
            "cart_count": 0,
        },
    )
