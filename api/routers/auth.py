from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from models import Admin
from auth.utils import verify_password, create_access_token, get_current_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, current_admin: Admin = Depends(get_current_admin)):
    if current_admin:
        return RedirectResponse(url="/admin/items", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin or not verify_password(password, admin.hashed_password):
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Email ou mot de passe incorrect"},
            status_code=401,
        )
    token = create_access_token({"sub": admin.email})
    redirect = RedirectResponse(url="/admin/items", status_code=302)
    redirect.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=28800,
    )
    return redirect


@router.get("/logout")
def logout():
    redirect = RedirectResponse(url="/admin/login", status_code=302)
    redirect.delete_cookie("access_token")
    return redirect
