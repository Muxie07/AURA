
with open("backend/tests/conftest.py", "r") as f:
    content = f.read()

content = content.replace("id=uuid.uuid4(),", "id=_DEFAULT_ORG_ID,")

# Actually that might replace too many things, let's be precise:
content = content.replace("id=uuid.uuid4(),\n        name=\"Test Organization\"", "id=_DEFAULT_ORG_ID,\n        name=\"Test Organization\"")
content = content.replace("id=uuid.uuid4(),\n        organization_id=organization.id", "id=_DEFAULT_USER_ID,\n        organization_id=organization.id")

with open("backend/tests/conftest.py", "w") as f:
    f.write(content)

