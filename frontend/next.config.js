/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable React strict mode for better development experience
  reactStrictMode: true,

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },

  // Image optimization settings
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
    ],
  },

  // Experimental features
  experimental: {
    // Enable server actions
    serverActions: {
      bodySizeLimit: '10mb',
    },
  },

  // Webpack configuration for Three.js single instance
  // Prevents "Multiple instances of Three.js" warning from react-force-graph-3d
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      three: require.resolve('three'),
    };
    return config;
  },
};

module.exports = nextConfig;
