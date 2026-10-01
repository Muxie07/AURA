import io
with io.open("backend/tests/conftest.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.startswith("    def override_get_settings():"):
        new_lines.append(line)
    elif line.startswith("        return TEST_SETTINGS"):
        new_lines.append(line)
    elif line.startswith("    test_app.dependency_overrides[get_settings] = override_get_settings"):
        new_lines.append(line)
    else:
        new_lines.append(line)

with io.open("backend/tests/conftest.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
