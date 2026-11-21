with open('backend/app/tools/builtin/customers.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'like(f"%{query}%")',
    'like(f"%{query.replace(\'%\', r\'\\%\').replace(\'_\', r\'\\_\')}%", escape="\\\\")'
)

with open('backend/app/tools/builtin/customers.py', 'w', encoding='utf-8') as f:
    f.write(code)

with open('backend/app/tools/builtin/products.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace(
    'like(f"%{query}%")',
    'like(f"%{query.replace(\'%\', r\'\\%\').replace(\'_\', r\'\\_\')}%", escape="\\\\")'
)

with open('backend/app/tools/builtin/products.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Escaped wildcards")
