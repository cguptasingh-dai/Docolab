import type { NextConfig } from "next";
import withBundleAnalyzer from "@next/bundle-analyzer";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const rootDir = dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Pin the workspace root — a stray package-lock.json in a parent directory
  // otherwise makes Next infer the wrong root.
  turbopack: {
    root: rootDir,
  },
};

const bundleAnalyzer = withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

export default bundleAnalyzer(nextConfig);

