path = "frontend/src/app/evaluations/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace('className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"', 
                    'className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border text-gray-900 bg-white"')
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed css")
