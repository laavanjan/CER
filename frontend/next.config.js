/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produce a static HTML export compatible with HF Spaces Docker runtime.
  // The FastAPI backend serves the exported files and handles SPA fallback.
  output: "export",

  // Ensure each route gets an index.html file (e.g. /intake/index.html)
  trailingSlash: true,

  // Next.js image optimisation requires a running server — disable for static export.
  images: {
    unoptimized: true,
  },

  // NOTE: rewrites() are not supported with output:'export'.
  // In local development set NEXT_PUBLIC_API_URL=http://localhost:8000
  // in frontend/.env.local so the dev server can reach the FastAPI backend.
};

module.exports = nextConfig;
