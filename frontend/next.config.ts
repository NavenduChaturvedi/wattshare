import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep Turbopack's root at this project, rather than walking up to a
  // package-lock.json in the user's home directory.
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
