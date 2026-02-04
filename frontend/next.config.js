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

  // Webpack configuration for Three.js
  webpack: (config, { isServer }) => {
    const path = require('path');
    const webpack = require('webpack');
    // Get three package root (go up from build/ to package root)
    const threePackageRoot = path.join(path.dirname(require.resolve('three')), '..');

    // Resolve three to a single instance
    config.resolve.alias = {
      ...config.resolve.alias,
      three: require.resolve('three'),
    };

    // Plugin to rewrite three/examples/jsm paths
    config.plugins.push(
      new webpack.NormalModuleReplacementPlugin(
        /^three\/examples\/jsm\/.+/,
        (resource) => {
          const subPath = resource.request.replace(/^three\//, '');
          resource.request = path.join(threePackageRoot, subPath);
        }
      )
    );

    return config;
  },
};

module.exports = nextConfig;
