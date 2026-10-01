from decimal import Decimal

from pydantic import BaseModel


class QuotationLine(BaseModel):
    product_id: str
    description: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

class QuotationDraft(BaseModel):
    quotation_id: str
    customer_id: str
    customer_name: str
    lines: list[QuotationLine]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    currency: str
    status: str
