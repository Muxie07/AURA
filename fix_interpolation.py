import os
import glob
import re

files = glob.glob('frontend/src/app/**/*.tsx', recursive=True)
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find fetchApi('...${...}...') and replace with fetchApi(`...${...}...`)
    content = re.sub(r"fetchApi\('([^']*\$\{[^}]+\}[^']*)'\)", r"fetchApi(`\1`)", content)
    
    # Same for double quotes just in case
    content = re.sub(r'fetchApi\("([^"]*\$\{[^}]+\}[^"]*)"\)', r"fetchApi(`\1`)", content)

    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
