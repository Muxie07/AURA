path = "frontend/src/app/conversations/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

while lines[-1].strip() in ["", "}", "];", ");", "</div>"]:
    lines.pop()

lines.append("          </div>\n")  # Closes <div className="text-center mt-2">
lines.append("        </div>\n")    # Closes Input Area
lines.append("      </div>\n")      # Closes Right Panel
lines.append("    </div>\n")        # Closes Workspace
lines.append("  </div>\n")          # Closes Root
lines.append("  );\n")
lines.append("}\n")

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
