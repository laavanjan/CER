// Server component — exports generateStaticParams (required by output:export)
// and delegates all rendering to the client component below.
import ScanPageClient from "./ScanPageClient";

// Scan IDs are not known at build time; return empty array so Next.js
// generates no static pages at build — the SPA shell handles routing.
export function generateStaticParams() {
  return [];
}

export default function ScanPage() {
  return <ScanPageClient />;
}
