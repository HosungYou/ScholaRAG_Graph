'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Network,
  FolderOpen,
  Settings,
  Menu,
  X,
  Home,
  ChevronRight,
} from 'lucide-react';
import { useState, useCallback } from 'react';

interface Breadcrumb {
  label: string;
  href?: string;
}

interface HeaderProps {
  breadcrumbs?: Breadcrumb[];
  rightContent?: React.ReactNode;
}

export function Header({ breadcrumbs, rightContent }: HeaderProps) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleMobileMenu = useCallback(() => {
    setMobileMenuOpen((prev) => !prev);
  }, []);

  const navLinks = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/projects', label: 'Projects', icon: Network },
    { href: '/import', label: 'Import', icon: FolderOpen },
    { href: '/settings', label: 'Settings', icon: Settings },
  ];

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <header className="bg-white shadow-sm border-b sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Breadcrumbs */}
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-2 flex-shrink-0"
              aria-label="ScholaRAG Graph Home"
            >
              <Network className="w-8 h-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900 hidden sm:block">
                ScholaRAG Graph
              </span>
            </Link>

            {/* Breadcrumbs */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <nav aria-label="Breadcrumb" className="hidden md:flex items-center">
                {breadcrumbs.map((crumb, index) => (
                  <div key={index} className="flex items-center">
                    <ChevronRight className="w-4 h-4 text-gray-400 mx-2" />
                    {crumb.href ? (
                      <Link
                        href={crumb.href}
                        className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
                      >
                        {crumb.label}
                      </Link>
                    ) : (
                      <span className="text-sm text-gray-700 font-medium truncate max-w-[200px]">
                        {crumb.label}
                      </span>
                    )}
                  </div>
                ))}
              </nav>
            )}
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
            {navLinks.slice(0, 3).map((link) => {
              const Icon = link.icon;
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                    ${active
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }
                  `}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className="w-4 h-4" />
                  {link.label}
                </Link>
              );
            })}

            {/* Settings Icon */}
            <Link
              href="/settings"
              className={`
                p-2 rounded-lg transition-colors
                ${isActive('/settings')
                  ? 'bg-blue-50 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                }
              `}
              aria-label="Settings"
            >
              <Settings className="w-5 h-5" />
            </Link>
          </nav>

          {/* Right Content (custom actions) */}
          {rightContent && (
            <div className="hidden md:flex items-center ml-4">
              {rightContent}
            </div>
          )}

          {/* Mobile Menu Button */}
          <button
            onClick={toggleMobileMenu}
            className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t bg-white">
          <nav className="px-4 py-3 space-y-1" aria-label="Mobile navigation">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`
                    flex items-center gap-3 px-3 py-3 rounded-lg text-sm font-medium transition-colors
                    ${active
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-600 hover:bg-gray-50'
                    }
                  `}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className="w-5 h-5" />
                  {link.label}
                </Link>
              );
            })}
          </nav>

          {/* Mobile Right Content */}
          {rightContent && (
            <div className="px-4 pb-3">
              {rightContent}
            </div>
          )}
        </div>
      )}
    </header>
  );
}
