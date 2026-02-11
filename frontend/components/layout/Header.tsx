'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Hexagon,
  FolderOpen,
  Settings,
  Menu,
  X,
  Home,
  ChevronRight,
  LayoutGrid,
} from 'lucide-react';
import { useState, useCallback } from 'react';
import { ScholaRAGLogo } from '@/components/ui/ScholaRAGLogo';
import { UserMenu } from '@/components/auth';

/* ============================================================
   Header - VS Design Diverge Style
   Direction B (T-Score 0.4) "Editorial Research"

   Design Principles:
   - No rounded corners (use 0 or minimal radius)
   - No blue colors (use accent-teal for active states)
   - Line-based hierarchy (border-bottom, not shadows)
   - Left accent bar for active items
   - Monospace labels for navigation
   - Dark/light theme support via CSS variables
   ============================================================ */

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
    { href: '/projects', label: 'Projects', icon: LayoutGrid },
    { href: '/import', label: 'Import', icon: FolderOpen },
  ];

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href);
  };

  return (
    <header className="bg-paper dark:bg-ink border-b border-ink/10 dark:border-paper/10 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 md:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Breadcrumbs */}
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="flex-shrink-0 hover:opacity-80 transition-opacity"
              aria-label="ScholaRAG Graph Home"
            >
              <ScholaRAGLogo size="md" showText />
            </Link>

            {/* Breadcrumbs - Line separated */}
            {breadcrumbs && breadcrumbs.length > 0 && (
              <nav aria-label="Breadcrumb" className="hidden md:flex items-center">
                <span className="w-px h-4 bg-ink/20 dark:bg-paper/20 mx-4" />
                {breadcrumbs.map((crumb, index) => (
                  <div key={index} className="flex items-center">
                    {index > 0 && (
                      <ChevronRight className="w-3 h-3 text-muted mx-2" />
                    )}
                    {crumb.href ? (
                      <Link
                        href={crumb.href}
                        className="font-mono text-xs uppercase tracking-wider text-muted hover:text-ink dark:hover:text-paper transition-colors"
                      >
                        {crumb.label}
                      </Link>
                    ) : (
                      <span className="font-mono text-xs uppercase tracking-wider text-ink dark:text-paper truncate max-w-[200px]">
                        {crumb.label}
                      </span>
                    )}
                  </div>
                ))}
              </nav>
            )}
          </div>

          {/* Desktop Navigation - Line-based active indicator */}
          <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`
                    relative flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors
                    ${active
                      ? 'text-accent-teal'
                      : 'text-muted hover:text-ink dark:hover:text-paper'
                    }
                  `}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className="w-4 h-4" strokeWidth={active ? 2 : 1.5} />
                  <span className="font-mono text-xs uppercase tracking-wider">
                    {link.label}
                  </span>
                  {/* Bottom accent line for active state */}
                  {active && (
                    <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-accent-teal" />
                  )}
                </Link>
              );
            })}

            {/* Settings - Icon only */}
            <Link
              href="/settings"
              className={`
                relative p-2 transition-colors ml-2
                ${isActive('/settings')
                  ? 'text-accent-teal'
                  : 'text-muted hover:text-ink dark:hover:text-paper'
                }
              `}
              aria-label="Settings"
            >
              <Settings className="w-5 h-5" strokeWidth={isActive('/settings') ? 2 : 1.5} />
              {isActive('/settings') && (
                <span className="absolute bottom-0 left-1 right-1 h-0.5 bg-accent-teal" />
              )}
            </Link>
          </nav>

          {/* Right Content (custom actions like ThemeToggle) */}
          <div className="hidden md:flex items-center ml-4 pl-4 border-l border-ink/10 dark:border-paper/10 gap-3">
            {rightContent}
            <UserMenu />
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={toggleMobileMenu}
            className="md:hidden p-2 text-muted hover:text-ink dark:hover:text-paper transition-colors"
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

      {/* Mobile Menu - Slide down */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-ink/10 dark:border-paper/10 bg-paper dark:bg-ink">
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
                    relative flex items-center gap-3 px-3 py-3 text-sm font-medium transition-colors
                    ${active
                      ? 'text-accent-teal'
                      : 'text-muted hover:text-ink dark:hover:text-paper'
                    }
                  `}
                  aria-current={active ? 'page' : undefined}
                >
                  {/* Left accent bar for active state */}
                  {active && (
                    <span className="absolute left-0 top-1 bottom-1 w-0.5 bg-accent-teal" />
                  )}
                  <Icon className="w-5 h-5" strokeWidth={active ? 2 : 1.5} />
                  <span className="font-mono text-xs uppercase tracking-wider">
                    {link.label}
                  </span>
                </Link>
              );
            })}

            {/* Settings in mobile */}
            <Link
              href="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className={`
                relative flex items-center gap-3 px-3 py-3 text-sm font-medium transition-colors
                ${isActive('/settings')
                  ? 'text-accent-teal'
                  : 'text-muted hover:text-ink dark:hover:text-paper'
                }
              `}
              aria-current={isActive('/settings') ? 'page' : undefined}
            >
              {isActive('/settings') && (
                <span className="absolute left-0 top-1 bottom-1 w-0.5 bg-accent-teal" />
              )}
              <Settings className="w-5 h-5" strokeWidth={isActive('/settings') ? 2 : 1.5} />
              <span className="font-mono text-xs uppercase tracking-wider">
                Settings
              </span>
            </Link>
          </nav>

          {/* Mobile Right Content */}
          <div className="px-4 pb-4 pt-2 border-t border-ink/10 dark:border-paper/10 flex items-center justify-between">
            {rightContent}
            <UserMenu />
          </div>
        </div>
      )}
    </header>
  );
}
