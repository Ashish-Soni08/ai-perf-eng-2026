import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Use src/ directory for Next.js to avoid conflict with Python app/ directory
  reactCompiler: true,
  rewrites: async () => [
    {
      source: "/api/:path*",
      destination:
        process.env.NODE_ENV === "development"
          ? "http://127.0.0.1:8000/:path*"
          : "/api/:path*",
    },
  ],
};

export default nextConfig;
