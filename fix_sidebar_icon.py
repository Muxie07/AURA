path = "frontend/src/app/components/Sidebar.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Make sure BeakerIcon is imported.
import_old = "import {\n  HomeIcon,\n  CpuChipIcon,\n  ChatBubbleLeftRightIcon,\n  CheckBadgeIcon,\n  ChartBarIcon,\n  Cog6ToothIcon,\n  BookOpenIcon,\n  WrenchScrewdriverIcon\n} from '@heroicons/react/24/outline';"
import_new = "import {\n  HomeIcon,\n  CpuChipIcon,\n  ChatBubbleLeftRightIcon,\n  CheckBadgeIcon,\n  ChartBarIcon,\n  Cog6ToothIcon,\n  BookOpenIcon,\n  WrenchScrewdriverIcon,\n  BeakerIcon\n} from '@heroicons/react/24/outline';"
text = text.replace(import_old, import_new)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Sidebar icon updated.")
