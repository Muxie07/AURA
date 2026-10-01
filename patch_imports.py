files = [
    "backend/app/tools/builtin/customers.py",
    "backend/app/tools/builtin/products.py",
    "backend/app/tools/builtin/pricing.py",
    "backend/app/tools/builtin/quotations.py"
]

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        text = f.read()
    
    text = text.replace("from app.database.core import SessionFactory", "from app.database.base import get_session_factory\nSessionFactory = get_session_factory()")
    
    with open(file, "w", encoding="utf-8") as f:
        f.write(text)

print("Patched imports!")
