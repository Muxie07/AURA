import glob

for path in glob.glob("backend/tests/**/*.py", recursive=True):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    
    new_text = text.replace('"MODEL_PROVIDER"', '"PRIMARY_LLM_PROVIDER"')
    new_text = new_text.replace("'MODEL_PROVIDER'", "'PRIMARY_LLM_PROVIDER'")
    
    if new_text != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
