path = "frontend/src/app/conversations/page.tsx"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# The last lines are:
#         </div>
#       </div>
#     </div>
#       </div>
#     </div>
#   );
# }

# We want to remove the extra `</div>` tags.
# Let's just find the `  );\n` line from the bottom and keep only what's needed.
# Let's count them:
# <div className="flex flex-col h-[calc(100vh-4rem)]">   <-- Root
#   <div className="mb-6 shrink-0"> ... </div>
#   <div className="flex flex-1 overflow-hidden border border-gray-200 rounded-xl bg-white shadow-sm"> <-- Workspace
#     <div className="w-80 border-r border-gray-200 flex flex-col bg-gray-50/50"> <-- Left Sidebar
#     </div>
#     <div className="flex-1 flex flex-col min-w-0 bg-white"> <-- Right Panel
#       ...
#     </div>
#   </div>
# </div>

# So the end of the file should look exactly like:
#           <div className="text-center mt-2">
#             <span className="text-xs text-gray-400">AURA can execute actions and retrieve internal knowledge. Verify important information.</span>
#           </div>
#         </div>
#       </div>
#     </div>
#   </div>
#   );
# }

# Let's rewrite the end manually by stripping all `</div>` and `);` and `}` at the end and re-appending them correctly.

while lines[-1].strip() in ["", "}", "];", ");", "</div>"]:
    lines.pop()

lines.append("        </div>\n")  # Closes Input Area
lines.append("      </div>\n")  # Closes Right Panel
lines.append("    </div>\n")    # Closes Workspace
lines.append("  </div>\n")      # Closes Root
lines.append("  );\n")
lines.append("}\n")

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
