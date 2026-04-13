from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from auth.utils import verify_password, get_password_hash, create_access_token, get_current_customer
from database import get_db
from models import Customer

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def customer_login_page(request: Request, current_customer=Depends(get_current_customer)):
    if current_customer:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("shop/login.html", {"request": request})


@router.post("/login")
def customer_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.email == email, Customer.is_active == True).first()
    if not customer or not verify_password(password, customer.hashed_password):
        return templates.TemplateResponse(
            "shop/login.html",
            {"request": request, "error": "Email ou mot de passe incorrect"},
            status_code=401,
        )
    token = create_access_token({"sub": customer.email})
    redirect = RedirectResponse(url=next, status_code=302)
    redirect.set_cookie(key="customer_token", value=token, httponly=True, samesite="lax", max_age=28800)
    return redirect


@router.get("/register", response_class=HTMLResponse)
def customer_register_page(request: Request):
    return templates.TemplateResponse("shop/register.html", {"request": request})


@router.post("/register")
def customer_register(
    request: Request,
    email: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    password: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    db: Session = Depends(get_db),
):
    existing = db.query(Customer).filter(Customer.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "shop/register.html",
            {"request": request, "error": "Un compte existe déjà avec cet email"},
            status_code=400,
        )
    customer = Customer(
        email=email,
        first_name=first_name,
        last_name=last_name,
        hashed_password=get_password_hash(password),
        phone=phone or None,
        address=address or None,
    )
    db.add(customer)
    db.commit()
    # auto login
    token = create_access_token({"sub": customer.email})
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.set_cookie(key="customer_token", value=token, httponly=True, samesite="lax", max_age=28800)
    return redirect


@router.get("/logout")
def customer_logout():
    redirect = RedirectResponse(url="/", status_code=302)
    redirect.delete_cookie("customer_token")
    return redirect
