/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Node type colors
        'node-paper': '#3B82F6',      // Blue
        'node-author': '#10B981',     // Green
        'node-concept': '#8B5CF6',    // Purple
        'node-method': '#F59E0B',     // Amber
        'node-finding': '#EF4444',    // Red
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};
