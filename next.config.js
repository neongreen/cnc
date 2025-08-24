/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  distDir: "build/app",
  images: {
    unoptimized: true,
  },
}

module.exports = nextConfig
