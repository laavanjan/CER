"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { apiClient, type ControlResultRead } from "@/lib/api";

const OUTCOME_STYLES: Record<string, string> = {
  PASS:    "bg-green-100 text-green-800 border-green-200",
  PARTIAL: "bg-yellow-100 text-yellow-800 border-yellow-200",
  MISSING: "bg-red-100 text-red-800 border-red-200",
};

// Map control_id prefix → human-readable pillar name
const PILLAR_NAMES: Record<string, string> = {
  ACC: "Accountability",
  AUD: "Audit & Governance",
  BIA: "Bias & Fairness",
  CON: "Consent",
  DAT: "Data Provenance",
  DEP: "Dependency Management",
  DIS: "Disclosure",
  DOC: "Documentation",
  DRI: "Drift & Monitoring",
  ENV: "Environmental Impact",
  ESC: "Escalation",
  EXP: "Explainability",
  FAI: "Fairness Metrics",
  GOV: "Governance",
  HUM: "Human Override",
  INC: "Inclusion",
  MON: "Monitoring",
  PII: "PII & Privacy",
  PRI: "Privacy",
  RET: "Data Retention",
  RIS: "Risk Assessment",
  SAF: "Safety Testing",
  THR: "Threat Modelling",
  VER: "Version Management",
  WCA: "Accessibility (WCAG)",
};

function getPillar(controlId: string): string {
  const prefix = controlId.split("-")[0];
  return PILLAR_NAMES[prefix] ?? prefix;
}

function FindingCard({ finding }: { finding: ControlResultRead }) {
  const [expanded, setExpanded] = useState(false);
  const outcomeStyle = OUTCOME_STYLES[finding.outcome] ?? "bg-gray-100 text-gray-800 border-gray-200";

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-semibold text-gray-700">{finding.control_id}</span>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${outcomeStyle}`}>
            {finding.outcome}
          </span>
        </div>
        <span className="text-gray-400 text-sm">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 p-4 space-y-4">
          {finding.explanation && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Explanation</h4>
              <p className="text-sm text-gray-700">{finding.explanation}</p>
            </div>
          )}
          {finding.remediation && finding.outcome !== "PASS" && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Remediation</h4>
              <p className="text-sm text-gray-700 whitespace-pre-line">{finding.remediation}</p>
            </div>
          )}
          {finding.evidence && ((finding.evidence as { paths?: string[] }).paths?.length ?? 0) > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Evidence Paths</h4>
              <ul className="space-y-1">
                {((finding.evidence as { paths?: string[] }).paths ?? []).map((p) => (
                  <li key={p} className="text-xs font-mono text-blue-700 bg-blue-50 px-2 py-1 rounded">{p}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

type Filter = "ALL" | "PASS" | "PARTIAL" | "MISSING";

export default function ReportPageClient() {
  const params = useParams();
  const scanId = params.scanId as string;
  const [filter, setFilter] = useState<Filter>("ALL");

  const { data: findings = [], isLoading, isError } = useQuery({
    queryKey: ["findings", scanId],
    queryFn: () => apiClient.getFindings(scanId),
    enabled: !!scanId,
  });

  const total   = findings.length;
  const pass    = findings.filter((f) => f.outcome === "PASS").length;
  const partial = findings.filter((f) => f.outcome === "PARTIAL").length;
  const missing = findings.filter((f) => f.outcome === "MISSING").length;

  const filtered = filter === "ALL" ? findings : findings.filter((f) => f.outcome === filter);

  // Group filtered findings by pillar
  const grouped = filtered.reduce<Record<string, ControlResultRead[]>>((acc, f) => {
    const pillar = getPillar(f.control_id);
    if (!acc[pillar]) acc[pillar] = [];
    acc[pillar].push(f);
    return acc;
  }, {});

  const stats: { label: string; value: number; filterKey: Filter; active: string; inactive: string }[] = [
    {
      label: "Total", value: total, filterKey: "ALL",
      active:   "ring-2 ring-gray-400 bg-gray-100 border-gray-300 text-gray-900",
      inactive: "bg-gray-50 border-gray-200 text-gray-800 hover:bg-gray-100",
    },
    {
      label: "Pass", value: pass, filterKey: "PASS",
      active:   "ring-2 ring-green-500 bg-green-100 border-green-300 text-green-900",
      inactive: "bg-green-50 border-green-200 text-green-800 hover:bg-green-100",
    },
    {
      label: "Partial", value: partial, filterKey: "PARTIAL",
      active:   "ring-2 ring-yellow-500 bg-yellow-100 border-yellow-300 text-yellow-900",
      inactive: "bg-yellow-50 border-yellow-200 text-yellow-800 hover:bg-yellow-100",
    },
    {
      label: "Missing", value: missing, filterKey: "MISSING",
      active:   "ring-2 ring-red-500 bg-red-100 border-red-300 text-red-900",
      inactive: "bg-red-50 border-red-200 text-red-800 hover:bg-red-100",
    },
  ];

  if (isLoading) return <div className="max-w-2xl mx-auto text-center py-16"><p className="text-gray-500">Loading report…</p></div>;
  if (isError)   return <div className="max-w-2xl mx-auto text-center py-16"><p className="text-red-600">Failed to load report.</p></div>;

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Ethics Review Report</h1>
        <p className="text-sm text-gray-500">Scan ID: {scanId}</p>
      </div>

      {/* Stat filter buttons */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, filterKey, active, inactive }) => (
          <button
            key={label}
            onClick={() => setFilter(filterKey)}
            className={`p-4 rounded-lg border text-center transition-all cursor-pointer ${filter === filterKey ? active : inactive}`}
          >
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-sm font-medium">{label}</p>
          </button>
        ))}
      </div>

      {/* Progress bar */}
      {total > 0 && (
        <div className="mb-8">
          <div className="flex gap-1 h-3 rounded-full overflow-hidden">
            <div className="bg-green-500 transition-all" style={{ width: `${(pass / total) * 100}%` }} />
            <div className="bg-yellow-400 transition-all" style={{ width: `${(partial / total) * 100}%` }} />
            <div className="bg-red-400 transition-all"    style={{ width: `${(missing / total) * 100}%` }} />
          </div>
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{Math.round((pass / total) * 100)}% Pass</span>
            <span>{Math.round((partial / total) * 100)}% Partial</span>
            <span>{Math.round((missing / total) * 100)}% Missing</span>
          </div>
        </div>
      )}

      {/* Active filter label */}
      {filter !== "ALL" && (
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-500">
            Showing <span className="font-medium text-gray-800">{filtered.length}</span> {filter.toLowerCase()} controls
          </p>
          <button onClick={() => setFilter("ALL")} className="text-xs text-blue-600 hover:underline">
            Clear filter
          </button>
        </div>
      )}

      {/* Grouped findings */}
      {filtered.length === 0 ? (
        <p className="text-center text-gray-500 py-8">No controls match this filter.</p>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([pillar, items]) => (
            <div key={pillar}>
              <div className="flex items-center gap-3 mb-3">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{pillar}</h2>
                <span className="text-xs text-gray-400 font-medium">{items.length} control{items.length !== 1 ? "s" : ""}</span>
                <div className="flex-1 h-px bg-gray-200" />
              </div>
              <div className="space-y-3">
                {items.map((finding) => (
                  <FindingCard key={finding.id} finding={finding} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
