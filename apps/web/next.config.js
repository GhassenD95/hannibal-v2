/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const api = process.env.HANNIBAL_API_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${api}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;