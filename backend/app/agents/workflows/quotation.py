import uuid
from decimal import Decimal
from typing import Any

from app.agents.core.state import AgentAction
from app.agents.execution.actions import ActionExecutor
from app.agents.workflows.schemas import QuotationDraft, QuotationLine

# Mock Data
CUSTOMERS = {
    "CUST-001": {"id": "CUST-001", "name": "Acme Corp", "status": "ACTIVE"},
    "ABC": {"id": "CUST-ABC", "name": "ABC Logistics", "status": "ACTIVE"}
}

PRODUCTS = {
    "PROD-X": {"id": "PROD-X", "name": "Product X", "base_price": "100.00"},
    "X": {"id": "PROD-X", "name": "Product X", "base_price": "100.00"}
}

class RetrieveCustomerAction(ActionExecutor):
    @property
    def name(self) -> str:
        return "RETRIEVE_CUSTOMER"

    async def execute(self, action: AgentAction, context: dict[str, Any]) -> dict[str, Any]:
        customer_ref = action.arguments.get("customer_ref", "").upper()
        # Mock search
        for key, cust in CUSTOMERS.items():
            if key in customer_ref or customer_ref in cust["name"].upper():
                return {"found": True, "customer": cust}
        return {"found": False, "customer": None}

class RetrieveProductAction(ActionExecutor):
    @property
    def name(self) -> str:
        return "RETRIEVE_PRODUCT"

    async def execute(self, action: AgentAction, context: dict[str, Any]) -> dict[str, Any]:
        product_ref = action.arguments.get("product_ref", "").upper()
        for key, prod in PRODUCTS.items():
            if key in product_ref or product_ref in prod["name"].upper():
                return {"found": True, "product": prod}
        return {"found": False, "product": None}

class CalculateQuotationAction(ActionExecutor):
    @property
    def name(self) -> str:
        return "CALCULATE_QUOTATION"

    async def execute(self, action: AgentAction, context: dict[str, Any]) -> dict[str, Any]:
        # Strictly deterministic calculation based on arguments
        try:
            quantity = int(action.arguments.get("quantity", 0))
            unit_price = Decimal(str(action.arguments.get("unit_price", "0")))
            tax_rate = Decimal(str(action.arguments.get("tax_rate", "0.10")))

            subtotal = quantity * unit_price
            tax = subtotal * tax_rate
            total = subtotal + tax

            return {
                "subtotal": str(subtotal),
                "tax": str(tax),
                "total": str(total)
            }
        except Exception as e:
            return {"error": str(e)}

class CreateQuotationDraftAction(ActionExecutor):
    @property
    def name(self) -> str:
        return "CREATE_QUOTATION_DRAFT"

    async def execute(self, action: AgentAction, context: dict[str, Any]) -> dict[str, Any]:
        # Validate schema
        args = action.arguments

        try:
            lines = []
            for item in args.get("lines", []):
                lines.append(QuotationLine(
                    product_id=item["product_id"],
                    description=item["description"],
                    quantity=int(item["quantity"]),
                    unit_price=Decimal(str(item["unit_price"])),
                    subtotal=Decimal(str(item["subtotal"]))
                ))

            draft = QuotationDraft(
                quotation_id=f"Q-{str(uuid.uuid4())[:8]}",
                customer_id=args["customer_id"],
                customer_name=args["customer_name"],
                lines=lines,
                subtotal=Decimal(str(args["subtotal"])),
                tax=Decimal(str(args["tax"])),
                total=Decimal(str(args["total"])),
                currency=args.get("currency", "USD"),
                status="DRAFT"
            )
            return {"success": True, "draft": draft.model_dump(mode="json")}
        except Exception as e:
            return {"success": False, "error": f"Invalid quotation schema: {e}"}
