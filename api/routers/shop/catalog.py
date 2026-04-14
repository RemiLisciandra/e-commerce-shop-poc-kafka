import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth.utils import get_current_customer
from database import get_db
from models import Item, Customer, Order, OrderItem

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _cart_count(request: Request) -> int:
    raw = request.cookies.get("cart", "{}")
    try:
        cart = json.loads(raw)
        return sum(cart.values())
    except Exception:
        return 0


@router.get("/", response_class=HTMLResponse)
def catalog(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    items = db.query(Item).filter(Item.quantity > 0).order_by(Item.id.desc()).all()

    # Previously purchased items (re-order suggestions)
    reorder_items = []
    if current_customer:
        purchased_ids = (
            db.query(OrderItem.item_id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.customer_id == current_customer.id, Order.status == "confirmed")
            .distinct()
            .all()
        )
        purchased_ids = [pid[0] for pid in purchased_ids]
        if purchased_ids:
            reorder_items = (
                db.query(Item)
                .filter(Item.id.in_(purchased_ids), Item.quantity > 0)
                .order_by(Item.id.desc())
                .limit(8)
                .all()
            )

    return templates.TemplateResponse(
        "shop/catalog.html",
        {
            "request": request,
            "items": items,
            "reorder_items": reorder_items,
            "customer": current_customer,
            "cart_count": _cart_count(request),
        },
    )
