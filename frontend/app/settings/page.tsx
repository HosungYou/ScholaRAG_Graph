'use client';

import { useState } from 'react';
import { Settings, Sun, Moon, Monitor, Database, Cpu, Globe } from 'lucide-react';
import { Header, Footer } from '@/components/layout';
import { ThemeToggle, ErrorBoundary } from '@/components/ui';
import { useTheme } from '@/hooks/useTheme';

export default function SettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [llmProvider, setLlmProvider] = useState('anthropic');
  const [language, setLanguage] = useState('ko');

  const themeOptions = [
    { value: 'light' as const, label: '라이트 모드', icon: Sun, description: '항상 밝은 테마 사용' },
    { value: 'dark' as const, label: '다크 모드', icon: Moon, description: '항상 어두운 테마 사용' },
    { value: 'system' as const, label: '시스템 설정', icon: Monitor, description: '시스템 설정에 따라 자동 전환' },
  ];

  const llmOptions = [
    { value: 'anthropic', label: 'Claude (Anthropic)', description: 'Claude 3.5 Haiku' },
    { value: 'openai', label: 'GPT-4 (OpenAI)', description: 'GPT-4o' },
    { value: 'google', label: 'Gemini (Google)', description: 'Gemini 1.5 Pro' },
  ];

  const languageOptions = [
    { value: 'ko', label: '한국어', flag: '🇰🇷' },
    { value: 'en', label: 'English', flag: '🇺🇸' },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      <a href="#main-content" className="skip-link">
        메인 콘텐츠로 건너뛰기
      </a>

      <Header
        breadcrumbs={[{ label: 'Settings' }]}
        rightContent={<ThemeToggle />}
      />

      <main id="main-content" className="flex-1 max-w-3xl mx-auto px-4 py-6 sm:py-8 w-full">
        <ErrorBoundary>
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-6 flex items-center gap-3">
            <Settings className="w-6 h-6" />
            설정
          </h2>

          <div className="space-y-6">
            {/* Theme Settings */}
            <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-5 sm:p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Sun className="w-5 h-5 text-yellow-500" />
                테마 설정
              </h3>
              <div className="grid sm:grid-cols-3 gap-3">
                {themeOptions.map((option) => {
                  const Icon = option.icon;
                  const isSelected = theme === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => setTheme(option.value)}
                      className={`
                        p-4 rounded-lg border-2 text-left transition-all touch-target
                        ${isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                        }
                      `}
                      aria-pressed={isSelected}
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <Icon className={`w-5 h-5 ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}`} />
                        <span className={`font-medium ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-white'}`}>
                          {option.label}
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                        {option.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </section>

            {/* LLM Provider Settings */}
            <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-5 sm:p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-purple-500" />
                AI 모델 설정
              </h3>
              <div className="space-y-3">
                {llmOptions.map((option) => {
                  const isSelected = llmProvider === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => setLlmProvider(option.value)}
                      className={`
                        w-full p-4 rounded-lg border-2 text-left transition-all flex items-center justify-between touch-target
                        ${isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                        }
                      `}
                      aria-pressed={isSelected}
                    >
                      <div>
                        <span className={`font-medium ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-white'}`}>
                          {option.label}
                        </span>
                        <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
                          {option.description}
                        </p>
                      </div>
                      {isSelected && (
                        <span className="text-blue-600 dark:text-blue-400 text-lg">✓</span>
                      )}
                    </button>
                  );
                })}
              </div>
              <p className="mt-4 text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                선택한 AI 모델은 채팅 및 엔티티 추출에 사용됩니다.
              </p>
            </section>

            {/* Language Settings */}
            <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-5 sm:p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Globe className="w-5 h-5 text-green-500" />
                언어 설정
              </h3>
              <div className="flex gap-3">
                {languageOptions.map((option) => {
                  const isSelected = language === option.value;
                  return (
                    <button
                      key={option.value}
                      onClick={() => setLanguage(option.value)}
                      className={`
                        flex-1 p-4 rounded-lg border-2 text-center transition-all touch-target
                        ${isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'
                        }
                      `}
                      aria-pressed={isSelected}
                    >
                      <span className="text-2xl mb-2 block">{option.flag}</span>
                      <span className={`font-medium ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-gray-900 dark:text-white'}`}>
                        {option.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>

            {/* Database Info */}
            <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-5 sm:p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <Database className="w-5 h-5 text-blue-500" />
                데이터베이스 정보
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center py-2 border-b dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">데이터베이스</span>
                  <span className="text-gray-900 dark:text-white font-mono">PostgreSQL + pgvector</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b dark:border-gray-700">
                  <span className="text-gray-500 dark:text-gray-400">호스팅</span>
                  <span className="text-gray-900 dark:text-white font-mono">Supabase</span>
                </div>
                <div className="flex justify-between items-center py-2">
                  <span className="text-gray-500 dark:text-gray-400">벡터 차원</span>
                  <span className="text-gray-900 dark:text-white font-mono">1536</span>
                </div>
              </div>
            </section>
          </div>
        </ErrorBoundary>
      </main>

      <Footer minimal />
    </div>
  );
}
