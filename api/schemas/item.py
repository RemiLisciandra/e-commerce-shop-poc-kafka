from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    price_ht: float
    tva_rate: float = 20.0
    quantity: int = 0


class ItemCreate(ItemBase):
    pass


class ItemUpdate(ItemBase):
    pass


class ItemResponse(ItemBase):
    id: int
    price_ttc: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
