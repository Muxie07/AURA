with open('backend/app/api/v1/runs.py', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('}\n\n"', '}\\n\\n"')
with open('backend/app/api/v1/runs.py', 'w', encoding='utf-8') as f:
    f.write(text)
