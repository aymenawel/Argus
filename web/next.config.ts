import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // The default bottom-left spot covers the rail's Settings link.
  devIndicators: { position: "bottom-right" },
};

export default nextConfig;
