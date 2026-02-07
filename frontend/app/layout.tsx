import type { Metadata } from 'next';
import { Inter, JetBrains_Mono, Crimson_Pro } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { ToastProvider } from '@/components/ui/Toast';

/* ============================================================
   ScholaRAG Graph - "Editorial Research" Typography Setup
   VS Design Diverge: Direction B (T-Score 0.4)

   Font Strategy:
   - Display (Headings): Crimson Pro (elegant serif alternative to Instrument Serif)
   - Body: Inter (clean, readable sans-serif)
   - Data/Metrics: JetBrains Mono (technical, monospace)
   ============================================================ */

// Body Text - Inter (Variable)
const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

// Data & Metrics - JetBrains Mono
const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jetbrains',
  display: 'swap',
  weight: ['400', '500', '600'],
});

// Display Headings - Crimson Pro (Scholarly Serif)
// High-contrast serif that conveys academic authority
const crimsonPro = Crimson_Pro({
  subsets: ['latin'],
  variable: '--font-instrument', // Using same variable name for consistency
  display: 'swap',
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
});

export const metadata: Metadata = {
  title: 'ScholaRAG Graph',
  description: 'Concept-Centric Knowledge Graph Platform for Systematic Literature Review',
  keywords: [
    'knowledge graph',
    'systematic review',
    'literature review',
    'PRISMA 2020',
    'research automation',
    'concept extraction',
  ],
  authors: [{ name: 'ScholaRAG Team' }],
  openGraph: {
    title: 'ScholaRAG Graph',
    description: 'Concept-Centric Knowledge Graph Platform for Systematic Literature Review',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${jetbrainsMono.variable} ${crimsonPro.variable}`}
    >
      <head>
        {/* Preconnect for performance */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="font-body antialiased">
        <Providers>
          <ToastProvider>{children}</ToastProvider>
        </Providers>
      </body>
    </html>
  );
}
