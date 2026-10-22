// The browser talks to the API on the same origin (/api, /mock-portal); Next proxies to the backend.
// One URL then serves everything, which is what a phone through a tunnel needs. Fixed at build time.
const backend = (process.env.BACKEND_INTERNAL_URL || "http://localhost:8000").replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  compress: false, // gzip would buffer the live dashboard's server-sent events
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/mock-portal/:path*", destination: `${backend}/mock-portal/:path*` },
      { source: "/webhooks/:path*", destination: `${backend}/webhooks/:path*` }, // Twilio / Meta webhooks via the tunnel
    ];
  },
};
export default nextConfig;
