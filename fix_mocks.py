import os

def fix_customers():
    path = "backend/app/tools/builtin/customers.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Replace the hardcoded global dict with a function
    text = text.replace(
        """CUSTOMERS = {
    "CUST-001": {"id": "CUST-001", "name": "Acme Industries", "email": "contact@acme.com", "org_id": "43d85a04-0ba3-4162-b8c0-4611fce533b3"},
    "CUST-002": {"id": "CUST-002", "name": "Globex Corp", "email": "info@globex.com", "org_id": "43d85a04-0ba3-4162-b8c0-4611fce533b3"}
}""",
        """def get_customers(org_id: str):
    return {
        f"CUST-001-{org_id[:8]}": {"id": f"CUST-001-{org_id[:8]}", "name": "Acme Technologies", "email": "contact@acme.com", "org_id": org_id},
        f"CUST-002-{org_id[:8]}": {"id": f"CUST-002-{org_id[:8]}", "name": "Globex Corp", "email": "info@globex.com", "org_id": org_id}
    }"""
    )
    
    text = text.replace("for c in CUSTOMERS.values():", "for c in get_customers(str(context.organization_id)).values():")
    text = text.replace("customer = CUSTOMERS.get(cust_id)", "customer = get_customers(str(context.organization_id)).get(cust_id)")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def fix_products():
    path = "backend/app/tools/builtin/products.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    text = text.replace(
        """PRODUCTS = {
    "PROD-X": {"id": "PROD-X", "name": "Enterprise Database Server", "sku": "ENT-DB-001", "availability": "in_stock", "org_id": "43d85a04-0ba3-4162-b8c0-4611fce533b3"},
    "PROD-Y": {"id": "PROD-Y", "name": "Load Balancer Advanced", "sku": "LB-ADV-002", "availability": "in_stock", "org_id": "43d85a04-0ba3-4162-b8c0-4611fce533b3"}
}""",
        """def get_products(org_id: str):
    return {
        f"PROD-X-{org_id[:8]}": {"id": f"PROD-X-{org_id[:8]}", "name": "Enterprise Database Server", "sku": "ENT-DB-001", "availability": "in_stock", "org_id": org_id},
        f"PROD-Y-{org_id[:8]}": {"id": f"PROD-Y-{org_id[:8]}", "name": "Load Balancer Advanced", "sku": "LB-ADV-002", "availability": "in_stock", "org_id": org_id}
    }"""
    )
    
    text = text.replace("for p in PRODUCTS.values():", "for p in get_products(str(context.organization_id)).values():")
    text = text.replace("product = PRODUCTS.get(prod_id)", "product = get_products(str(context.organization_id)).get(prod_id)")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def fix_quotations():
    path = "backend/app/tools/builtin/quotations.py"
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
        
    text = text.replace("from app.tools.builtin.customers import CUSTOMERS", "from app.tools.builtin.customers import get_customers")
    text = text.replace("from app.tools.builtin.products import PRODUCTS", "from app.tools.builtin.products import get_products")
    
    text = text.replace("if cust_id not in CUSTOMERS or CUSTOMERS[cust_id][\"org_id\"] != str(context.organization_id):", 
                       "customers = get_customers(str(context.organization_id))\n    if cust_id not in customers or customers[cust_id][\"org_id\"] != str(context.organization_id):")
    
    text = text.replace("if prod_id not in PRODUCTS or PRODUCTS[prod_id][\"org_id\"] != str(context.organization_id):",
                       "products = get_products(str(context.organization_id))\n        if prod_id not in products or products[prod_id][\"org_id\"] != str(context.organization_id):")
    
    text = text.replace("prod_id == \"PROD-X\"", "prod_id.startswith(\"PROD-X\")")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

fix_customers()
fix_products()
fix_quotations()
print("Fixed mocks")
