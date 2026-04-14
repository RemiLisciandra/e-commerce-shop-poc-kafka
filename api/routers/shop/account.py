import io
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fpdf import FPDF
from sqlalchemy.orm import Session, joinedload

from auth.utils import get_current_customer
from database import get_db
from models import Customer, Order, OrderItem, Payment, Invoice, Item

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _require_customer(customer):
    if not customer:
        return RedirectResponse(url="/login?next=/account", status_code=302)
    return None


def _cart_count(request: Request) -> int:
    import json
    try:
        return sum(json.loads(request.cookies.get("cart", "{}")).values())
    except Exception:
        return 0


# ── Purchase history ──────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def account_history(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    guard = _require_customer(current_customer)
    if guard:
        return guard

    orders = (
        db.query(Order)
        .filter(Order.customer_id == current_customer.id)
        .options(joinedload(Order.items).joinedload(OrderItem.item))
        .order_by(Order.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "shop/account/history.html",
        {
            "request": request,
            "orders": orders,
            "customer": current_customer,
            "cart_count": _cart_count(request),
        },
    )


# ── Payments list ─────────────────────────────────────────────────────────────

@router.get("/payments", response_class=HTMLResponse)
def account_payments(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    guard = _require_customer(current_customer)
    if guard:
        return guard

    payments = (
        db.query(Payment)
        .join(Order, Order.id == Payment.order_id)
        .filter(Order.customer_id == current_customer.id)
        .order_by(Payment.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "shop/account/payments.html",
        {
            "request": request,
            "payments": payments,
            "customer": current_customer,
            "cart_count": _cart_count(request),
        },
    )


# ── Invoices list ─────────────────────────────────────────────────────────────

@router.get("/invoices", response_class=HTMLResponse)
def account_invoices(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    guard = _require_customer(current_customer)
    if guard:
        return guard

    invoices = (
        db.query(Invoice)
        .join(Order, Order.id == Invoice.order_id)
        .filter(Order.customer_id == current_customer.id)
        .order_by(Invoice.issued_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "shop/account/invoices.html",
        {
            "request": request,
            "invoices": invoices,
            "customer": current_customer,
            "cart_count": _cart_count(request),
        },
    )


# ── PDF Invoice download ─────────────────────────────────────────────────────

@router.get("/invoices/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    if not current_customer:
        return RedirectResponse(url="/login", status_code=302)

    invoice = (
        db.query(Invoice)
        .join(Order, Order.id == Invoice.order_id)
        .filter(Invoice.id == invoice_id, Order.customer_id == current_customer.id)
        .first()
    )
    if not invoice:
        return RedirectResponse(url="/account/invoices", status_code=302)

    order = invoice.order
    order_items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order.id)
        .options(joinedload(OrderItem.item))
        .all()
    )

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "ShopItem", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Facture {invoice.invoice_number}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Date : {invoice.issued_at.strftime('%d/%m/%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Echeance : {invoice.due_date.strftime('%d/%m/%Y') if invoice.due_date else '-'}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Customer info
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Client", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, f"{current_customer.first_name} {current_customer.last_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, current_customer.email, new_x="LMARGIN", new_y="NEXT")
    if current_customer.address:
        pdf.cell(0, 5, current_customer.address, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Table header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(80, 8, "Article", border=1, fill=True)
    pdf.cell(20, 8, "Qte", border=1, fill=True, align="C")
    pdf.cell(30, 8, "P.U. HT", border=1, fill=True, align="R")
    pdf.cell(30, 8, "P.U. TTC", border=1, fill=True, align="R")
    pdf.cell(30, 8, "Total TTC", border=1, fill=True, align="R")
    pdf.ln()

    # Table rows
    pdf.set_font("Helvetica", "", 9)
    for oi in order_items:
        title = oi.item.title if oi.item else "Article supprime"
        # Truncate long titles
        if len(title) > 40:
            title = title[:37] + "..."
        line_ttc = round(oi.unit_price_ttc * oi.quantity, 2)
        pdf.cell(80, 7, title, border=1)
        pdf.cell(20, 7, str(oi.quantity), border=1, align="C")
        pdf.cell(30, 7, f"{oi.unit_price_ht:.2f} EUR", border=1, align="R")
        pdf.cell(30, 7, f"{oi.unit_price_ttc:.2f} EUR", border=1, align="R")
        pdf.cell(30, 7, f"{line_ttc:.2f} EUR", border=1, align="R")
        pdf.ln()

    pdf.ln(4)

    # Totals
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(130, 7, "", border=0)
    pdf.cell(30, 7, "Total HT", border=0, align="R")
    pdf.cell(30, 7, f"{invoice.total_ht:.2f} EUR", border=0, align="R")
    pdf.ln()
    pdf.cell(130, 7, "", border=0)
    pdf.cell(30, 7, "TVA", border=0, align="R")
    pdf.cell(30, 7, f"{invoice.total_tva:.2f} EUR", border=0, align="R")
    pdf.ln()
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(130, 8, "", border=0)
    pdf.cell(30, 8, "Total TTC", border="T", align="R")
    pdf.cell(30, 8, f"{invoice.total_ttc:.2f} EUR", border="T", align="R")

    buf = io.BytesIO(pdf.output())
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'},
    )


# ── Profile edit ─────────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
def account_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    guard = _require_customer(current_customer)
    if guard:
        return guard

    return templates.TemplateResponse(
        "shop/account/profile.html",
        {
            "request": request,
            "customer": current_customer,
            "cart_count": _cart_count(request),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@router.post("/profile")
def account_profile_save(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    db: Session = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    guard = _require_customer(current_customer)
    if guard:
        return guard

    current_customer.first_name = first_name.strip()
    current_customer.last_name = last_name.strip()
    current_customer.phone = phone.strip() or None
    current_customer.address = address.strip() or None
    db.commit()

    return RedirectResponse(url="/account/profile?saved=1", status_code=303)
