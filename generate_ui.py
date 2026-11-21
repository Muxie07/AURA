import os

app_dir = 'frontend/src/app'

def create_dir(path):
    os.makedirs(os.path.join(app_dir, path), exist_ok=True)

dirs = ['components', 'agents', 'conversations', 'knowledge', 'tools', 'approvals', 'observability', 'settings']
for d in dirs:
    create_dir(d)

layout_content = """import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "./components/Sidebar";
import Topnav from "./components/Topnav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AURA | Enterprise AI Platform",
  description: "Production-quality AURA frontend",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased bg-gray-50`}>
      <body className="min-h-full flex h-full overflow-hidden text-gray-900">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <Topnav />
          <main className="flex-1 overflow-y-auto bg-gray-50">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
"""

with open(os.path.join(app_dir, 'layout.tsx'), 'w', encoding='utf-8') as f:
    f.write(layout_content)

print("Setup directories and layout successfully.")
