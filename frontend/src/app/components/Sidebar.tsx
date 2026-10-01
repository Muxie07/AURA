'use client';
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
