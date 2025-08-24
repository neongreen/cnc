/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  distDir: "build/app",
  images: {
    unoptimized: true,
  },
  basePath: "/cnc",
}

module.exports = nextConfig
