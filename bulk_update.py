import os
import glob
import re

files = glob.glob('frontend/src/app/**/*.tsx', recursive=True)
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    content = re.sub(
        r"const token = localStorage\.getItem\('token'\) \|\| 'test-token';\s*const headers = \{ 'Authorization': `Bearer \$\{token\}` \};\s*const API_URL = process\.env\.NEXT_PUBLIC_API_URL \|\| 'http://localhost:8000/api/v1';",
        "",
        content
    )
    content = re.sub(
        r"const token = localStorage\.getItem\('token'\) \|\| 'test-token';\s*const API_URL = process\.env\.NEXT_PUBLIC_API_URL \|\| 'http://localhost:8000/api/v1';",
        "",
        content
    )
    
    # fetch(`${API_URL}/endpoint`, { headers }) -> fetchApi('/endpoint')
    content = re.sub(r"fetch\(`\$\{API_URL\}([^`]+)`, \{[^}]*headers[^}]*\}\)", r"fetchApi('\1')", content)
    # fetch(`${API_URL}/endpoint`) -> fetchApi('/endpoint')
    content = re.sub(r"fetch\(`\$\{API_URL\}([^`]+)`\)", r"fetchApi('\1')", content)

    if content != original_content:
        if 'import { fetchApi }' not in content:
            depth = file.replace('\\', '/').count('/') - 3
            import_path = '../' * depth + 'lib/api' if depth > 0 else './lib/api'
            import_stmt = f"import {{ fetchApi }} from '{import_path}';\n"
            content = import_stmt + content

        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
            print(f"Updated {file}")
