import type { NextConfig } from "next";
const config: NextConfig = {
 output: "standalone",
 experimental: { proxyTimeout: 120000 },
 async rewrites() { return [{source: "/api/:path*", destination: "http://api:8000/:path*"}]; },
 turbopack: { rules: {"*.css": {loaders: ["@tailwindcss/turbopack"], as: "*.css"}}}
};
export default config;
