import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow cross-origin requests from external origins in development
  allowedDevOrigins: [
    "46.225.22.208",
    "http://46.225.22.208:3001",
    "http://46.225.22.208",
  ],

  async rewrites() {
    return [
      {
        // Rewrite non-streaming API requests to backend
        // Note: /api/v1/chat/stream is handled by route handler, not this rewrite
        source: "/api/:path*",
        destination: "http://localhost:9000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
