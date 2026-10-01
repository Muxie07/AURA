path = "frontend/src/app/components/Sidebar.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Add BeakerIcon to imports
import_str = "import { HomeIcon, CpuChipIcon, ChatBubbleLeftRightIcon, CheckBadgeIcon, ChartBarIcon, Cog6ToothIcon, BookOpenIcon, WrenchScrewdriverIcon } from '@heroicons/react/24/outline';"
new_import = "import { HomeIcon, CpuChipIcon, ChatBubbleLeftRightIcon, CheckBadgeIcon, ChartBarIcon, Cog6ToothIcon, BookOpenIcon, WrenchScrewdriverIcon, BeakerIcon } from '@heroicons/react/24/outline';"
text = text.replace(import_str, new_import)

# Add Evaluations to navigation array
nav_str = "{ name: 'Settings', href: '/settings', icon: Cog6ToothIcon },"
new_nav = "{ name: 'Evaluations', href: '/evaluations', icon: BeakerIcon },\n  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },"
text = text.replace(nav_str, new_nav)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Sidebar updated.")
