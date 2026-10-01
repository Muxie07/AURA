files = [
    "backend/app/tools/builtin/customers.py",
    "backend/app/tools/builtin/products.py",
    "backend/app/tools/builtin/pricing.py",
    "backend/app/tools/builtin/quotations.py"
]

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        text = f.read()
    
    text = text.replace("SessionFactory = get_session_factory()\n", "")
    text = text.replace("async with SessionFactory() as db:", "async with get_session_factory()() as db:")
    
    with open(file, "w", encoding="utf-8") as f:
        f.write(text)

print("Patched imports again!")
