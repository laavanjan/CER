/** @type {import('next').NextConfig} */

// output:'export' is only needed for the Docker / HF Spaces production build.
// In local development it breaks dynamic routes with runtime UUIDs (scan IDs,
// report IDs) because the static exporter requires every param to be known at
// build time.  Set NEXT_EXPORT=true in the Docker build to enable it.
const isExport = process.env.NEXT_EXPORT === "true";

const nextConfig = {
  // Only produce a static HTML export in production Docker builds.
  ...(isExport && { output: "export" }),

  // Ensure each route gets an index.html file (e.g. /intake/index.html).
  // Kept on in both modes so URLs are consistent.
  trailingSlash: true,

  // Next.js image optimisation requires a running server — disable so both
  // dev and static-export modes work without an image optimisation server.
  images: {
    unoptimized: true,
  },

  // NOTE: rewrites() are not supported with output:'export'.
  // In local development set NEXT_PUBLIC_API_URL=http://localhost:8000
  // in frontend/.env.local so the dev server can reach the FastAPI backend.
};

module.exports = nextConfig;
