'use client';

import Link from 'next/link';
import { Github, ExternalLink } from 'lucide-react';

interface FooterProps {
  minimal?: boolean;
}

export function Footer({ minimal = false }: FooterProps) {
  if (minimal) {
    return (
      <footer className="border-t bg-white py-4">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-500">
          ScholaRAG Graph &copy; {new Date().getFullYear()}
        </div>
      </footer>
    );
  }

  return (
    <footer className="border-t bg-white mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Brand */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">ScholaRAG Graph</h3>
            <p className="text-sm text-gray-600">
              AGENTiGraph-style Knowledge Graph Platform for Academic Literature
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Quick Links</h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link href="/projects" className="text-gray-600 hover:text-gray-900 transition-colors">
                  Projects
                </Link>
              </li>
              <li>
                <Link href="/import" className="text-gray-600 hover:text-gray-900 transition-colors">
                  Import Data
                </Link>
              </li>
              <li>
                <Link href="/settings" className="text-gray-600 hover:text-gray-900 transition-colors">
                  Settings
                </Link>
              </li>
            </ul>
          </div>

          {/* Tech Stack */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Built With</h4>
            <p className="text-sm text-gray-600">
              Next.js, React Flow, FastAPI, PostgreSQL
            </p>
            <div className="mt-4 flex items-center gap-3">
              <a
                href="https://github.com/HosungYou/ScholaRAG"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="GitHub Repository"
              >
                <Github className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t text-center text-sm text-gray-500">
          <p>&copy; {new Date().getFullYear()} ScholaRAG Graph. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
