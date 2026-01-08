'use client';

import { Sun, Moon, Monitor } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { useState, useRef, useEffect } from 'react';

interface ThemeToggleProps {
  variant?: 'icon' | 'dropdown';
}

export function ThemeToggle({ variant = 'icon' }: ThemeToggleProps) {
  const { theme, resolvedTheme, setTheme, toggleTheme, isDark } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  if (variant === 'icon') {
    return (
      <button
        onClick={toggleTheme}
        className="p-2 rounded-lg text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
        aria-label={isDark ? '라이트 모드로 전환' : '다크 모드로 전환'}
      >
        {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
      </button>
    );
  }

  const options = [
    { value: 'light' as const, label: '라이트', icon: Sun },
    { value: 'dark' as const, label: '다크', icon: Moon },
    { value: 'system' as const, label: '시스템', icon: Monitor },
  ];

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 transition-colors"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="테마 선택"
      >
        {isDark ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
        <span className="text-sm hidden sm:inline">
          {theme === 'system' ? '시스템' : isDark ? '다크' : '라이트'}
        </span>
      </button>

      {isOpen && (
        <div
          className="absolute right-0 mt-2 w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-1 z-50"
          role="listbox"
        >
          {options.map((option) => {
            const Icon = option.icon;
            const isSelected = theme === option.value;
            return (
              <button
                key={option.value}
                onClick={() => {
                  setTheme(option.value);
                  setIsOpen(false);
                }}
                className={`
                  w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors
                  ${isSelected
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
                    : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700'
                  }
                `}
                role="option"
                aria-selected={isSelected}
              >
                <Icon className="w-4 h-4" />
                {option.label}
                {isSelected && (
                  <span className="ml-auto text-blue-600 dark:text-blue-400">✓</span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
