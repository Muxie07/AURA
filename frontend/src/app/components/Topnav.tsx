'use client';
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
