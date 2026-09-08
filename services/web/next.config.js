/** @type {import('next').NextConfig} */
const apiInternal =
  process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://api:8000";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiInternal}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
