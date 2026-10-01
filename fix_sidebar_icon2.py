path = "frontend/src/app/components/Sidebar.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("Cog6ToothIcon \n}", "Cog6ToothIcon, \n  BeakerIcon \n}")
text = text.replace("Cog6ToothIcon\n}", "Cog6ToothIcon,\n  BeakerIcon\n}")

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
