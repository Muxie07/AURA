path = "backend/app/ai/providers/heuristic.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

import re
text = text.replace(
    r"""ready_steps.append((match.group(1), action))""",
    r"""ready_steps.append((match.group(1), action))
            
            if not ready_steps:
                import structlog
                logger = structlog.get_logger(__name__)
                logger.error("HEURISTIC_REGEX_FAILED", sys_prompt=sys_prompt)
                if "customer.search" in sys_prompt:
                    ready_steps.append(("step_1", "customer.search"))
                elif "quotation.create_draft" in sys_prompt:
                    ready_steps.append(("step_2", "quotation.create_draft"))"""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Added regex fallback")
