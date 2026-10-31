import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // `npm run replay` builds into its own folder so it can run beside `next dev` (D-83).
  distDir: process.env.ARGUS_DIST_DIR || ".next",
  cacheComponents: true,
  partialPrefetching: true,
  // The default bottom-left spot covers the rail's Settings link.
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;
