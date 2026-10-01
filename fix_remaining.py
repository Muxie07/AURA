import os
import glob
import re

files = glob.glob('frontend/src/app/**/*.tsx', recursive=True)
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    content = re.sub(r"const res = await fetch\(`\$\{API_URL\}([^`]+)`, \{\n\s*headers: \{ 'Authorization': `Bearer \$\{token\}` \}\n\s*\}\);", r"const res = await fetchApi('\1');", content)

    if content != original:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
            print(f"Fixed {file}")
