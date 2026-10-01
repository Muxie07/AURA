with open("backend/app/ai/providers/google.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("async async def generate", "async def generate")
text = text.replace("async async def generate_structured", "async def generate_structured")

with open("backend/app/ai/providers/google.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed async syntax in google.py")
