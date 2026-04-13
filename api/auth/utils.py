from datetime import datetime, timedelta
from typing import Optional
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Admin, Customer

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 heures

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def get_current_admin(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Optional[Admin]:
    email = _decode_token(access_token)
    if not email:
        return None
    return db.query(Admin).filter(Admin.email == email, Admin.is_active == True).first()


def get_current_customer(
    customer_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Optional[Customer]:
    email = _decode_token(customer_token)
    if not email:
        return None
    return db.query(Customer).filter(Customer.email == email, Customer.is_active == True).first()
