import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow cross-origin requests from external origins in development
  allowedDevOrigins: [
    "46.225.22.208",
    "http://46.225.22.208:3001",
    "http://46.225.22.208",
  ],

  // Note: API routes are handled by Next.js route handlers in app/api/
  // which proxy to the backend and transform responses as needed.
  // No rewrites needed since all routes have explicit handlers.
};

export default nextConfig;
