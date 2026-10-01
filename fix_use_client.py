import os
import glob

files = glob.glob('frontend/src/app/**/*.tsx', recursive=True)
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    if any("'use client';" in line for line in lines):
        # Remove all instances of 'use client';
        clean_lines = [line for line in lines if "'use client';" not in line]
        # Insert at the very top
        clean_lines.insert(0, "'use client';\n")
        
        with open(file, 'w', encoding='utf-8') as f:
            f.writelines(clean_lines)
            print(f"Fixed use client in {file}")
