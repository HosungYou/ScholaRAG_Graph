'use client';

import Link from 'next/link';
import { FolderOpen, MessageSquare, Network, Plus } from 'lucide-react';
import { Header, Footer } from '@/components/layout';
import { ThemeToggle } from '@/components/ui';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex flex-col">
      {/* Skip Link for Accessibility */}
      <a href="#main-content" className="skip-link">
        메인 콘텐츠로 건너뛰기
      </a>

      <Header
        rightContent={<ThemeToggle variant="dropdown" />}
      />

      {/* Hero Section */}
      <main id="main-content" className="flex-1 max-w-7xl mx-auto px-4 py-8 sm:py-12 w-full">
        <div className="text-center mb-8 sm:mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4">
            Explore Your Research Literature
          </h2>
          <p className="text-lg sm:text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            AGENTiGraph-style Knowledge Graph platform for visualizing and
            exploring academic literature from ScholaRAG.
          </p>
        </div>

        {/* Quick Actions */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-8 sm:mb-12">
          <Link
            href="/import"
            className="group p-5 sm:p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 hover:shadow-md transition-all touch-target"
          >
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-lg group-hover:bg-blue-200 dark:group-hover:bg-blue-900/50 transition-colors">
                <FolderOpen className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Import ScholaRAG
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-300">
              Import your existing ScholaRAG project folders and build a
              knowledge graph automatically.
            </p>
          </Link>

          <Link
            href="/projects"
            className="group p-5 sm:p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 hover:shadow-md transition-all touch-target"
          >
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-green-100 dark:bg-green-900/30 rounded-lg group-hover:bg-green-200 dark:group-hover:bg-green-900/50 transition-colors">
                <Network className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Explore Graphs
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-300">
              Visualize and explore your knowledge graphs with interactive
              React Flow interface.
            </p>
          </Link>

          <Link
            href="/projects"
            className="group p-5 sm:p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 hover:shadow-md transition-all touch-target sm:col-span-2 lg:col-span-1"
          >
            <div className="flex items-center gap-4 mb-4">
              <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg group-hover:bg-purple-200 dark:group-hover:bg-purple-900/50 transition-colors">
                <MessageSquare className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Chat with AI
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-300">
              Ask questions about your literature and get graph-grounded
              responses with citations.
            </p>
          </Link>
        </div>

        {/* Features */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border dark:border-gray-700 p-6 sm:p-8">
          <h3 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white mb-6">Features</h3>
          <div className="grid sm:grid-cols-2 gap-4 sm:gap-6">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400 font-bold">1</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Dual-Mode Interface</h4>
                <p className="text-gray-600 dark:text-gray-300 text-sm sm:text-base">
                  Switch between Chatbot Mode and Exploration Mode seamlessly.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400 font-bold">2</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Multi-Agent System</h4>
                <p className="text-gray-600 dark:text-gray-300 text-sm sm:text-base">
                  6-agent pipeline for intelligent query processing and reasoning.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400 font-bold">3</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Graph-Grounded Responses</h4>
                <p className="text-gray-600 dark:text-gray-300 text-sm sm:text-base">
                  Every AI response is linked to actual nodes in your knowledge graph.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 dark:text-blue-400 font-bold">4</span>
              </div>
              <div>
                <h4 className="font-semibold text-gray-900 dark:text-white">Multi-Provider LLM</h4>
                <p className="text-gray-600 dark:text-gray-300 text-sm sm:text-base">
                  Choose between Claude, GPT-4, or Gemini for your AI interactions.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
