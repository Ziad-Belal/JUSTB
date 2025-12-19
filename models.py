# retail_store_management/models.py

from datetime import datetime
from typing import Optional

class User:
    def __init__(self, id: Optional[int], username: str, password_hash: str, role: str, created_at: Optional[datetime] = None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role # 'admin' or 'worker'
        self.created_at = created_at if created_at else datetime.now()

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

class Product:
    def __init__(self, id: Optional[int], name: str, description: Optional[str], price: float,
                 stock_quantity: int, qr_code_path: Optional[str] = None,
                 created_at: Optional[datetime] = None, updated_at: Optional[datetime] = None):
        self.id = id
        self.name = name
        self.description = description
        self.price = price
        self.stock_quantity = stock_quantity
        self.qr_code_path = qr_code_path
        self.created_at = created_at if created_at else datetime.now()
        self.updated_at = updated_at if updated_at else datetime.now()

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price}, stock={self.stock_quantity})>"

class Promotion:
    def __init__(self, id: Optional[int], code: str, discount_percentage: float,
                 start_date: datetime, end_date: datetime, is_active: bool = True,
                 created_at: Optional[datetime] = None):
        self.id = id
        self.code = code
        self.discount_percentage = discount_percentage
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = is_active
        self.created_at = created_at if created_at else datetime.now()

    def __repr__(self):
        return f"<Promotion(id={self.id}, code='{self.code}', discount={self.discount_percentage}%)>"

class Sale:
    def __init__(self, id: Optional[int], user_id: int, total_amount: float,
                 discount_amount: float, final_amount: float, promotion_id: Optional[int] = None,
                 sale_date: Optional[datetime] = None):
        self.id = id
        self.user_id = user_id
        self.total_amount = total_amount
        self.discount_amount = discount_amount
        self.final_amount = final_amount
        self.promotion_id = promotion_id
        self.sale_date = sale_date if sale_date else datetime.now()

    def __repr__(self):
        return f"<Sale(id={self.id}, user_id={self.user_id}, final_amount={self.final_amount})>"

class SaleItem:
    def __init__(self, id: Optional[int], sale_id: int, product_id: int,
                 quantity: int, price_at_sale: float):
        self.id = id
        self.sale_id = sale_id
        self.product_id = product_id
        self.quantity = quantity
        self.price_at_sale = price_at_sale

    def __repr__(self):
        return f"<SaleItem(id={self.id}, sale_id={self.sale_id}, product_id={self.product_id}, qty={self.quantity})>"