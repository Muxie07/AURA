with open("backend/app/database/models.py", "a") as f:
    f.write("""
class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))

class Product(Base):
    __tablename__ = "products"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(100))
    availability: Mapped[str] = mapped_column(String(50))
    base_price: Mapped[float] = mapped_column(sa.Float, default=0.0)

class Quotation(Base):
    __tablename__ = "quotations"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(_JSON_TYPE, default=list)
    total: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
""")
