import path from "node:path";

import type { NextConfig } from "next";

const API_DEV = process.env.API_DEV ?? "http://127.0.0.1:8000";

// Produksi hanya berisi file statis. Rewrite dipakai saat `next dev` saja,
// karena di produksi Nginx yang meneruskan /api/ ke Django.
const dasar: NextConfig = {
  turbopack: {
    root: path.resolve("."),
    rules: {
      "*.css": { loaders: ["@tailwindcss/turbopack"], as: "*.css" },
    },
  },
};

const nextConfig: NextConfig =
  process.env.NODE_ENV === "production"
    ? {
        ...dasar,
        output: "export",
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : {
        ...dasar,
        trailingSlash: true,
        skipTrailingSlashRedirect: true,
        async rewrites() {
          return [
            { source: "/api/:path*/", destination: `${API_DEV}/api/:path*/` },
            { source: "/api/:path*", destination: `${API_DEV}/api/:path*` },
          ];
        },
      };

export default nextConfig;
