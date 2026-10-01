with open("backend/app/tools/builtin/__init__.py", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_import = "from app.tools.registry import ToolRegistry"
new_import = "from app.tools.builtin.observability import ObservabilityExecutor\nfrom app.tools.registry import ToolRegistry"

text = text.replace(old_import, new_import)

old_reg = "    registry.register(communication_create_email_draft_tool)"
new_reg = "    registry.register(communication_create_email_draft_tool)\n    registry.register(ObservabilityExecutor())"

text = text.replace(old_reg, new_reg)

with open("backend/app/tools/builtin/__init__.py", "w", encoding="utf-8") as f:
    f.write(text)
