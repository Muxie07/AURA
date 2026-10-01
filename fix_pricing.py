path = "backend/app/tools/builtin/pricing.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("from app.tools.builtin.products import PRODUCTS", "from app.tools.builtin.products import get_products")
text = text.replace("product = PRODUCTS.get(prod_id)", "product = get_products(str(context.organization_id)).get(prod_id)")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed pricing")
