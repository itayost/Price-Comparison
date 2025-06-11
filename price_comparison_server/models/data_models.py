from pydantic import BaseModel
from typing import List, Optional

class Price(BaseModel):
    snif_key: str
    item_code: str
    item_name: str
    item_price: float
    timestamp: str

class CartItem(BaseModel):
    item_name: str
    quantity: int

class CartRequest(BaseModel):
    city: str
    items: List[CartItem]

class SaveCartRequest(BaseModel):
    cart_name: str
    email: str
    city: str
    items: List[CartItem]