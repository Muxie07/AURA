with open("backend/scripts/seed_demo.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """        session.add_all([u1_admin, u1_manager, u1_demo, u1_analyst, u2_admin, u3_admin])
        await session.flush()"""

replacement = """        session.add_all([u1_admin, u1_manager, u1_demo, u1_analyst, u2_admin, u3_admin])
        await session.flush()

        # Demo Entity Identifiers expected by heuristic
        org1_hex = str(org1.id).replace("-", "")[:8]
        org1_uuid_str = str(org1.id)[:8] # e.g. "a2f37be1"

        cust1 = Customer(id="cust-001", organization_id=org1.id, name="Acme Technologies", email="contact@acme.com")
        cust2 = Customer(id=f"CUST-001-{org1_uuid_str}", organization_id=org1.id, name="Acme Technologies (Fallback)", email="contact2@acme.com")
        cust3 = Customer(id="CUST-003", organization_id=org1.id, name="Nova Engineering", email="procurement@nova.net")
        
        # Products
        prod1 = Product(id=f"PROD-X-{org1_uuid_str}", organization_id=org1.id, name="Enterprise Database Server", sku="ENT-DB-001", availability="in_stock", base_price=5000.00)
        prod2 = Product(id="prod-x", organization_id=org1.id, name="Enterprise Database Server", sku="ENT-DB-002", availability="in_stock", base_price=5000.00)
        prod3 = Product(id="PROD-X", organization_id=org1.id, name="Enterprise Database Server", sku="ENT-DB-003", availability="in_stock", base_price=5000.00)
        prod4 = Product(id="PROD-AI", organization_id=org1.id, name="AI Analytics Platform", sku="AI-PLAT-100", availability="in_stock", base_price=3500.00)

        session.add_all([cust1, cust2, cust3, prod1, prod2, prod3, prod4])
        await session.flush()"""

# We must FIRST remove the previous patch if it exists, otherwise it will append again if we use the target
import re
text = re.sub(r'        # Business Entities \(Demo DB overrides\).*?await session\.flush\(\)', '', text, flags=re.DOTALL)

if target in text:
    text = text.replace(target, replacement)
    with open("backend/scripts/seed_demo.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Patched seed_demo.py successfully with heuristics!")
else:
    print("Target block not found in seed_demo.py")
