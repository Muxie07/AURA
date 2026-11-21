import os

app_dir = 'frontend/src/app'

sidebar_content = """'use client';
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
  Cog6ToothIcon 
} from '@heroicons/react/24/outline';

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'AI Agents', href: '/agents', icon: CpuChipIcon },
  { name: 'Conversations', href: '/conversations', icon: ChatBubbleLeftRightIcon },
  { name: 'Knowledge', href: '/knowledge', icon: BookOpenIcon },
  { name: 'Tools', href: '/tools', icon: WrenchScrewdriverIcon },
  { name: 'Approvals', href: '/approvals', icon: CheckBadgeIcon },
  { name: 'Observability', href: '/observability', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];

function classNames(...classes: string[]) {
  return classes.filter(Boolean).join(' ');
}

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-16 shrink-0 items-center px-6 border-b border-gray-200">
        <h1 className="text-xl font-bold tracking-tight text-blue-600">AURA</h1>
      </div>
      <nav className="flex flex-1 flex-col overflow-y-auto pt-4 px-3 pb-4">
        <ul role="list" className="flex flex-1 flex-col gap-y-7">
          <li>
            <ul role="list" className="-mx-2 space-y-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <li key={item.name}>
                    <Link
                      href={item.href}
                      className={classNames(
                        isActive
                          ? 'bg-blue-50 text-blue-600'
                          : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50',
                        'group flex gap-x-3 rounded-md p-2 text-sm leading-6 font-semibold'
                      )}
                    >
                      <item.icon
                        className={classNames(
                          isActive ? 'text-blue-600' : 'text-gray-400 group-hover:text-blue-600',
                          'h-6 w-6 shrink-0'
                        )}
                        aria-hidden="true"
                      />
                      {item.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </li>
        </ul>
      </nav>
    </div>
  );
}
"""

topnav_content = """'use client';
import { BellIcon } from '@heroicons/react/24/outline';

export default function Topnav() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-6 lg:px-8">
      <div className="flex flex-1">
        {/* Breadcrumb or search could go here */}
      </div>
      <div className="flex items-center gap-x-4 lg:gap-x-6">
        <button type="button" className="-m-2.5 p-2.5 text-gray-400 hover:text-gray-500">
          <span className="sr-only">View notifications</span>
          <BellIcon className="h-6 w-6" aria-hidden="true" />
        </button>
        <div className="hidden lg:block lg:h-6 lg:w-px lg:bg-gray-200" aria-hidden="true" />
        <div className="flex items-center gap-x-4">
          <div className="h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center text-sm font-semibold text-gray-600">
            A
          </div>
          <span className="hidden lg:flex lg:items-center">
            <span className="ml-2 text-sm font-semibold leading-6 text-gray-900" aria-hidden="true">
              Admin User
            </span>
          </span>
        </div>
      </div>
    </header>
  );
}
"""

with open(os.path.join(app_dir, 'components', 'Sidebar.tsx'), 'w', encoding='utf-8') as f:
    f.write(sidebar_content)

with open(os.path.join(app_dir, 'components', 'Topnav.tsx'), 'w', encoding='utf-8') as f:
    f.write(topnav_content)

print("Components written.")
