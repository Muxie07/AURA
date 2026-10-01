with open("backend/scripts/seed_demo.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add imports
content = content.replace("ToolExecutionAudit, User", "ToolExecutionAudit, User, Customer, Product, Quotation")

# Find the spot to insert demo records. We can put it after "session.add(org1)" or at the end.
# It's better to put it after we have org1.id
seed_data = """
        # Demo Business Entities
        cust1 = Customer(id=f"CUST-001-{str(org1.id)[:8]}", organization_id=org1.id, name="Acme Technologies", email="contact@acme.com")
        cust2 = Customer(id=f"CUST-002-{str(org1.id)[:8]}", organization_id=org1.id, name="Globex Corp", email="info@globex.com")
        
        prod1 = Product(id=f"PROD-X-{str(org1.id)[:8]}", organization_id=org1.id, name="Enterprise Database Server", sku="ENT-DB-001", availability="in_stock", base_price=100.00)
        prod2 = Product(id=f"PROD-Y-{str(org1.id)[:8]}", organization_id=org1.id, name="Load Balancer Advanced", sku="LB-ADV-002", availability="in_stock", base_price=50.00)
        
        session.add_all([cust1, cust2, prod1, prod2])
        await session.commit()
"""

if "cust1 = Customer" not in content:
    content = content.replace("print('Demo organization and user created.')", seed_data + "\n        print('Demo organization and user created.')")

with open("backend/scripts/seed_demo.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated seed_demo.py")
