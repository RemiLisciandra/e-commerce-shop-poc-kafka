import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth.utils import get_current_admin
from database import get_db
from models import Item, Admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TVA_RATES = [0.0, 5.5, 10.0, 20.0]
UPLOADS_DIR = "/app/uploads"


def _require_admin(current_admin: Optional[Admin]) -> Optional[RedirectResponse]:
    if not current_admin:
        return RedirectResponse(url="/admin/login", status_code=302)
    return None


def _save_upload(file: UploadFile) -> Optional[str]:
    """Save uploaded file and return its public path, or None if no file."""
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    if ext not in allowed:
        return None
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = os.path.join(UPLOADS_DIR, filename)
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(file.file.read())
    return f"/uploads/{filename}"


def _delete_upload(image_url: Optional[str]) -> None:
    if image_url and image_url.startswith("/uploads/"):
        path = "/app" + image_url
        try:
            os.remove(path)
        except OSError:
            pass


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/items", response_class=HTMLResponse)
def list_items(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Optional[Admin] = Depends(get_current_admin),
):
    guard = _require_admin(current_admin)
    if guard:
        return guard
    items = db.query(Item).order_by(Item.id.desc()).all()
    return templates.TemplateResponse(
        "admin/items/list.html",
        {"request": request, "items": items, "user": current_admin},
    )


# ── Create ────────────────────────────────────────────────────────────────────

@router.get("/items/create", response_class=HTMLResponse)
def create_item_form(
    request: Request,
    current_admin: Optional[Admin] = Depends(get_current_admin),
):
    guard = _require_admin(current_admin)
    if guard:
        return guard
    return templates.TemplateResponse(
        "admin/items/create.html",
        {"request": request, "user": current_admin, "tva_rates": TVA_RATES},
    )


@router.post("/items/create")
def create_item(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    price_ht: float = Form(...),
    tva_rate: float = Form(20.0),
    quantity: int = Form(0),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_admin: Optional[Admin] = Depends(get_current_admin),
):
    guard = _require_admin(current_admin)
    if guard:
        return guard
    image_url = _save_upload(image)
    price_ttc = round(price_ht * (1 + tva_rate / 100), 2)
    item = Item(
        title=title,
        description=description or None,
        image_url=image_url,
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
    current_admin: Optional[Admin] = Depends(get_current_admin),
):
    guard = _require_admin(current_admin)
    if guard:
        return guard
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        return RedirectResponse(url="/admin/items", status_code=302)
    return templates.TemplateResponse(
        "admin/items/edit.html",
        {"request": request, "item": item, "user": current_admin, "tva_rates": TVA_RATES},
    )


@router.post("/items/{item_id}/edit")
def edit_item(
    item_id: int,
    title: str = Form(...),
    description: str = Form(""),
    price_ht: float = Form(...),
    tva_rate: float = Form(20.0),
    quantity: int = Form(0),
    image: UploadFile = File(None),
    remove_image: str = Form(""),
    db: Session = Depends(get_db),
    current_admin: Optional[Admin] = Depends(get_current_admin),
):
    guard = _require_admin(current_admin)
    if guard:
        return guard
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        return RedirectResponse(url="/admin/items", status_code=302)

    item.title = title
    item.description = description or None
    item.price_ht = price_ht
    item.tva_rate = tva_rate
    item.price_ttc = round(price_ht * (1 + tva_rate / 100), 2)
    item.quantity = quantity

    new_image = _save_upload(image)
    if new_image:
        _delete_upload(item.image_url)
        item.image_url = new_image
    elif remove_image == "1":
        _delete_upload(item.image_url)
        item.image_url = None

    db.commit()
    return RedirectResponse(url="/admin/items", status_code=302)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.post("/items/{item_id}/delete")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_admin: Optional[Admin] = Depends(get_current_admin),
):
    guard = _require_admin(current_admin)
    if guard:
        return guard
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        _delete_upload(item.image_url)
        db.delete(item)
        db.commit()
    return RedirectResponse(url="/admin/items", status_code=302)
