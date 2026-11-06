/** @type {import('next').NextConfig} */
const BACKEND_URL = (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig = {
  reactStrictMode: true,
  experimental: { proxyTimeout: 180000 }, // AI calls (resume analysis, feedback) can take a while
  async rewrites() {
    // The browser talks to /api/* on the Next.js origin; Next forwards it to FastAPI. No CORS, cookies just work.
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};
export default nextConfig;
