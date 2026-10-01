import os

with open("patch_main.py", "r") as f:
    c = f.read()

target = "c = c.replace('def create_app() -> FastAPI:', middlewares_code + '\\n\\ndef create_app() -> FastAPI:')"
c = c.replace(target, '')

target2 = 'with open("backend/app/main.py", "w") as f:\n    f.write(c)'
replacement2 = target + '\n\n' + target2
c = c.replace(target2, replacement2)

with open("patch_main.py", "w") as f:
    f.write(c)
