import re

with open('backend/app/database/models.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix Customer
code = re.sub(
    r'class Customer\(TimestampMixin, Base\):\n    __tablename__ = "customers"\n    id: Mapped\[uuid\.UUID\] = mapped_column\(_UUID_TYPE, primary_key=True, default=uuid\.uuid4\)',
    'class Customer(TimestampMixin, Base):\n    __tablename__ = "customers"\n    id: Mapped[str] = mapped_column(String(50), primary_key=True)',
    code
)

# Fix Product
code = re.sub(
    r'class Product\(TimestampMixin, Base\):\n    __tablename__ = "products"\n    id: Mapped\[uuid\.UUID\] = mapped_column\(_UUID_TYPE, primary_key=True, default=uuid\.uuid4\)',
    'class Product(TimestampMixin, Base):\n    __tablename__ = "products"\n    id: Mapped[str] = mapped_column(String(50), primary_key=True)',
    code
)

# Fix Quotation
code = re.sub(
    r'class Quotation\(TimestampMixin, Base\):\n    __tablename__ = "quotations"\n    id: Mapped\[uuid\.UUID\] = mapped_column\(_UUID_TYPE, primary_key=True, default=uuid\.uuid4\)\n    organization_id: Mapped\[uuid\.UUID\] = mapped_column\(ForeignKey\("organizations\.id", ondelete="CASCADE"\), index=True\)\n    customer_id: Mapped\[uuid\.UUID\] = mapped_column\(ForeignKey\("customers\.id", ondelete="CASCADE"\), index=True\)',
    'class Quotation(TimestampMixin, Base):\n    __tablename__ = "quotations"\n    id: Mapped[str] = mapped_column(String(50), primary_key=True)\n    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)\n    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)',
    code
)

# Fix QuotationItem
code = re.sub(
    r'class QuotationItem\(TimestampMixin, Base\):\n    __tablename__ = "quotation_items"\n    id: Mapped\[uuid\.UUID\] = mapped_column\(_UUID_TYPE, primary_key=True, default=uuid\.uuid4\)\n    quotation_id: Mapped\[uuid\.UUID\] = mapped_column\(ForeignKey\("quotations\.id", ondelete="CASCADE"\), index=True\)\n    product_id: Mapped\[uuid\.UUID\] = mapped_column\(ForeignKey\("products\.id", ondelete="RESTRICT"\), index=True\)',
    'class QuotationItem(TimestampMixin, Base):\n    __tablename__ = "quotation_items"\n    id: Mapped[uuid.UUID] = mapped_column(_UUID_TYPE, primary_key=True, default=uuid.uuid4)\n    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id", ondelete="CASCADE"), index=True)\n    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=True)',
    code
)

with open('backend/app/database/models.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Fixed String PKs')
