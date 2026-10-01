from app.tools.builtin.communications import communication_create_email_draft_tool
from app.tools.builtin.crm import crm_create_activity_tool
from app.tools.builtin.customers import customer_get_tool, customer_search_tool
from app.tools.builtin.observability import observability_get_api_latency_tool
from app.tools.builtin.pricing import pricing_calculate_tool, pricing_get_tool
from app.tools.builtin.products import product_get_tool, product_search_tool
from app.tools.builtin.quotations import quotation_create_draft_tool
from app.tools.registry import ToolRegistry


def register_builtin_tools(registry: ToolRegistry) -> None:
    registry.register(customer_search_tool)
    registry.register(customer_get_tool)
    registry.register(product_search_tool)
    registry.register(product_get_tool)
    registry.register(pricing_get_tool)
    registry.register(pricing_calculate_tool)
    registry.register(quotation_create_draft_tool)
    registry.register(crm_create_activity_tool)
    registry.register(communication_create_email_draft_tool)
    registry.register(observability_get_api_latency_tool)
