import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',  // Important for Docker deployment
  env: {
    BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000',
  },
  images: {
    unoptimized: true,  // Required for static export
  },
};

export default nextConfig;
