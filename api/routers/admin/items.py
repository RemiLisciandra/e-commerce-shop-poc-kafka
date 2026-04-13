from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth.utils import get_current_user
from database import get_db
from models import Item, User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TVA_RATES = [0.0, 5.5, 10.0, 20.0]


def _require_admin(current_user: Optional[User]) -> Optional[RedirectResponse]:
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    return None


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/items", response_class=HTMLResponse)
def list_items(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    guard = _require_admin(current_user)
    if guard:
        return guard
    items = db.query(Item).order_by(Item.id.desc()).all()
    return templates.TemplateResponse(
        "admin/items/list.html",
        {"request": request, "items": items, "user": current_user},
    )


# ── Create ────────────────────────────────────────────────────────────────────

@router.get("/items/create", response_class=HTMLResponse)
def create_item_form(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
):
    guard = _require_admin(current_user)
    if guard:
        return guard
    return templates.TemplateResponse(
        "admin/items/create.html",
        {"request": request, "user": current_user, "tva_rates": TVA_RATES},
    )


@router.post("/items/create")
def create_item(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    image_url: str = Form(""),
    price_ht: float = Form(...),
    tva_rate: float = Form(20.0),
    quantity: int = Form(0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    guard = _require_admin(current_user)
    if guard:
        return guard
    price_ttc = round(price_ht * (1 + tva_rate / 100), 2)
    item = Item(
        title=title,
        description=description or None,
        image_url=image_url or None,
        price_ht=price_ht,
        tva_rate=tva_rate,
        price_ttc=price_ttc,
        quantity=quantity,
    )
    db.add(item)
    db.commit()
    return RedirectResponse(url="/admin/items", status_code=302)


# ── Edit ──────────────────────────────────────────────────────────────────────

@router.get("/items/{item_id}/edit", response_class=HTMLResponse)
def edit_item_form(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    guard = _require_admin(current_user)
    if guard:
        return guard
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        return RedirectResponse(url="/admin/items", status_code=302)
    return templates.TemplateResponse(
        "admin/items/edit.html",
        {"request": request, "item": item, "user": current_user, "tva_rates": TVA_RATES},
    )


@router.post("/items/{item_id}/edit")
def edit_item(
    item_id: int,
    title: str = Form(...),
    description: str = Form(""),
    image_url: str = Form(""),
    price_ht: float = Form(...),
    tva_rate: float = Form(20.0),
    quantity: int = Form(0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    guard = _require_admin(current_user)
    if guard:
        return guard
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        return RedirectResponse(url="/admin/items", status_code=302)
    item.title = title
    item.description = description or None
    item.image_url = image_url or None
    item.price_ht = price_ht
    item.tva_rate = tva_rate
    item.price_ttc = round(price_ht * (1 + tva_rate / 100), 2)
    item.quantity = quantity
    db.commit()
    return RedirectResponse(url="/admin/items", status_code=302)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.post("/items/{item_id}/delete")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    guard = _require_admin(current_user)
    if guard:
        return guard
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/items", status_code=302)
