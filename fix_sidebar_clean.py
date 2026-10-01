path = "frontend/src/app/components/Sidebar.tsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Let's cleanly replace the import block and navigation block
# just in case there are invisible characters.
import_str = """'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  HomeIcon, 
  CpuChipIcon, 
  ChatBubbleLeftRightIcon, 
  BookOpenIcon, 
  WrenchScrewdriverIcon, 
  CheckBadgeIcon, 
  ChartBarIcon, 
  Cog6ToothIcon,
  BeakerIcon
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'AI Tasks', href: '/agents', icon: CpuChipIcon },
  { name: 'Conversations', href: '/conversations', icon: ChatBubbleLeftRightIcon },
  { name: 'Company Knowledge', href: '/knowledge', icon: BookOpenIcon },
  { name: 'Available Actions', href: '/tools', icon: WrenchScrewdriverIcon },
  { name: 'Approvals', href: '/approvals', icon: CheckBadgeIcon },
  { name: 'Observability', href: '/observability', icon: ChartBarIcon },
  { name: 'Evaluations', href: '/evaluations', icon: BeakerIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];"""

# Find the index of "function classNames"
idx = text.find("function classNames")
if idx != -1:
    new_text = import_str + "\n\n" + text[idx:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Cleaned up Sidebar.tsx")
else:
    print("Could not find function classNames")
