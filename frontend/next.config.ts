import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',  // Important for Docker deployment
  env: {
    BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  },
  images: {
    unoptimized: true,  // Required for static export
  },
  trailingSlash: true,
  
  // Disable ESLint errors during builds
  eslint: {
    ignoreDuringBuilds: true, // This will skip ESLint checks
  },
  
  // Disable TypeScript errors during builds
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
