"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { apiClient, type ControlResultRead } from "@/lib/api";

// Required for Next.js static export — scan IDs are not known at build time.
// The FastAPI SPA fallback serves index.html for unknown paths so the client-
// side router handles the route dynamically.
export function generateStaticParams() {
  return [];
}

const OUTCOME_STYLES: Record<string, string> = {
  PASS: "bg-green-100 text-green-800 border-green-200",
  PARTIAL: "bg-yellow-100 text-yellow-800 border-yellow-200",
  MISSING: "bg-red-100 text-red-800 border-red-200",
};

function FindingCard({ finding }: { finding: ControlResultRead }) {
  const [expanded, setExpanded] = useState(false);
  const outcomeStyle = OUTCOME_STYLES[finding.outcome] ?? "bg-gray-100 text-gray-800 border-gray-200";

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      {/* Header — always visible */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-semibold text-gray-700">
            {finding.control_id}
          </span>
          <span
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${outcomeStyle}`}
          >
            {finding.outcome}
          </span>
        </div>
        <span className="text-gray-400 text-sm">{expanded ? "▲" : "▼"}</span>
      </div>

      {/* Expandable detail */}
      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-4">
          {finding.explanation && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Explanation
              </h4>
              <p className="text-sm text-gray-700">{finding.explanation}</p>
            </div>
          )}

          {finding.remediation && finding.outcome !== "PASS" && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Remediation
              </h4>
              <p className="text-sm text-gray-700 whitespace-pre-line">{finding.remediation}</p>
            </div>
          )}

          {finding.evidence && ((finding.evidence as { paths?: string[] }).paths?.length ?? 0) > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Evidence Paths
              </h4>
              <ul className="space-y-1">
                {((finding.evidence as { paths?: string[] }).paths ?? []).map((p) => (
                  <li key={p} className="text-xs font-mono text-blue-700 bg-blue-50 px-2 py-1 rounded">
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const scanId = params.scanId as string;

  const { data: findings = [], isLoading, isError } = useQuery({
    queryKey: ["findings", scanId],
    queryFn: () => apiClient.getFindings(scanId),
    enabled: !!scanId,
  });

  const total = findings.length;
  const pass = findings.filter((f) => f.outcome === "PASS").length;
  const partial = findings.filter((f) => f.outcome === "PARTIAL").length;
  const missing = findings.filter((f) => f.outcome === "MISSING").length;

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <p className="text-gray-500">Loading report…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <p className="text-red-600">Failed to load report. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Ethics Review Report</h1>
        <p className="text-sm text-gray-500">Scan ID: {scanId}</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: "Total", value: total, color: "bg-gray-50 border-gray-200 text-gray-800" },
          { label: "Pass", value: pass, color: "bg-green-50 border-green-200 text-green-800" },
          { label: "Partial", value: partial, color: "bg-yellow-50 border-yellow-200 text-yellow-800" },
          { label: "Missing", value: missing, color: "bg-red-50 border-red-200 text-red-800" },
        ].map(({ label, value, color }) => (
          <div key={label} className={`p-4 rounded-lg border ${color} text-center`}>
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-sm font-medium">{label}</p>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="mb-8">
          <div className="flex gap-1 h-3 rounded-full overflow-hidden">
            <div
              className="bg-green-500 transition-all"
              style={{ width: `${(pass / total) * 100}%` }}
            />
            <div
              className="bg-yellow-400 transition-all"
              style={{ width: `${(partial / total) * 100}%` }}
            />
            <div
              className="bg-red-400 transition-all"
              style={{ width: `${(missing / total) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{Math.round((pass / total) * 100)}% Pass</span>
            <span>{Math.round((partial / total) * 100)}% Partial</span>
            <span>{Math.round((missing / total) * 100)}% Missing</span>
          </div>
        </div>
      )}

      {/* Per-control findings */}
      {findings.length === 0 ? (
        <p className="text-center text-gray-500">No findings available yet.</p>
      ) : (
        <div className="space-y-3">
          {findings.map((finding) => (
            <FindingCard key={finding.id} finding={finding} />
          ))}
        </div>
      )}
    </div>
  );
}
