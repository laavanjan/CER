"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { apiClient, type ControlResultRead } from "@/lib/api";

// Outcome styles — lowercase values from the new pipeline
const OUTCOME_CONFIG: Record<string, { label: string; badge: string; row: string }> = {
  pass:          { label: "Pass",          badge: "bg-emerald-100 text-emerald-700 border-emerald-200", row: "" },
  partial:       { label: "Partial",       badge: "bg-amber-100 text-amber-700 border-amber-200",      row: "" },
  missing:       { label: "Missing",       badge: "bg-red-100 text-red-700 border-red-200",            row: "bg-red-50/30" },
  not_evaluable: { label: "Supplement",    badge: "bg-purple-100 text-purple-700 border-purple-200",   row: "bg-purple-50/20" },
  not_triggered: { label: "Not triggered", badge: "bg-gray-100 text-gray-500 border-gray-200",         row: "" },
  // Legacy uppercase fallbacks
  PASS:          { label: "Pass",          badge: "bg-emerald-100 text-emerald-700 border-emerald-200", row: "" },
  PARTIAL:       { label: "Partial",       badge: "bg-amber-100 text-amber-700 border-amber-200",      row: "" },
  MISSING:       { label: "Missing",       badge: "bg-red-100 text-red-700 border-red-200",            row: "bg-red-50/30" },
};

const PILLAR_MAP: Record<string, string> = {
  ACC:  "Accessibility & Inclusion",
  DOC:  "Documentation & Traceability",
  FAIR: "Fairness & Non-Discrimination",
  FAI:  "Fairness & Non-Discrimination",
  GOV:  "Governance & Accountability",
  HUMO: "Human Oversight & Recourse",
  HUM:  "Human Oversight & Recourse",
  PRIV: "Data Governance & Privacy",
  PRI:  "Data Governance & Privacy",
  RISK: "Risk Management",
  RIS:  "Risk Management",
  SAFE: "Safety & Robustness",
  SAF:  "Safety & Robustness",
  SEC:  "Security & Misuse Prevention",
  SOC:  "Societal & Environmental",
  TRAN: "Transparency & Explainability",
  TRA:  "Transparency & Explainability",
};

function getPillar(controlId: string): string {
  const prefix = controlId.split("-")[0];
  return PILLAR_MAP[prefix] ?? prefix;
}

type RemediationStep = {
  step_number?: number;
  action?: string;
  artifact_to_produce?: string;
  example_approach?: string;
  priority?: string;
};

function parseRemediation(raw: string | null | undefined): RemediationStep[] | null {
  if (!raw) return null;
  // Try JSON parse first
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    if (parsed.remediation_steps) return parsed.remediation_steps;
  } catch {}
  // Try Python repr → JSON (replace single quotes, True/False/None)
  try {
    const jsonLike = raw
      .replace(/'/g, '"')
      .replace(/\bTrue\b/g, "true")
      .replace(/\bFalse\b/g, "false")
      .replace(/\bNone\b/g, "null");
    const parsed = JSON.parse(jsonLike);
    if (Array.isArray(parsed)) return parsed;
  } catch {}
  return null;
}

const PRIORITY_COLORS: Record<string, string> = {
  immediate:        "bg-red-50 text-red-700 border-red-200",
  before_reviewer:  "bg-amber-50 text-amber-700 border-amber-200",
  before_certifier: "bg-blue-50 text-blue-700 border-blue-200",
};

function FindingCard({ finding }: { finding: ControlResultRead }) {
  const [expanded, setExpanded] = useState(false);
  const outcome = (finding.outcome ?? "").toLowerCase();
  const cfg = OUTCOME_CONFIG[finding.outcome] ?? OUTCOME_CONFIG[outcome] ?? {
    label: finding.outcome, badge: "bg-gray-100 text-gray-600 border-gray-200", row: "",
  };
  const steps = parseRemediation(finding.remediation);
  const evidencePaths: string[] = (finding.evidence as { paths?: string[] } | null)?.paths ?? [];
  const isNotEvaluable = outcome === "not_evaluable";

  return (
    <div className={`rounded-xl border border-gray-200 overflow-hidden transition-shadow hover:shadow-md ${cfg.row}`}>
      <button
        className="w-full flex items-center justify-between px-5 py-3.5 text-left hover:bg-gray-50/60 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="font-mono text-sm font-bold text-gray-800 flex-shrink-0">{finding.control_id}</span>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border flex-shrink-0 ${cfg.badge}`}>
            {cfg.label}
          </span>
          {isNotEvaluable && (
            <span className="text-xs text-purple-500 hidden sm:block">Human supplement required</span>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-5 bg-white">
          {/* Not evaluable notice */}
          {isNotEvaluable && (
            <div className="flex gap-3 p-3 bg-purple-50 border border-purple-100 rounded-lg">
              <span className="text-purple-500 text-lg leading-none">📋</span>
              <div>
                <p className="text-sm font-semibold text-purple-800">Design-only control — supplement required</p>
                <p className="text-xs text-purple-600 mt-0.5">
                  This control cannot be assessed from code alone. A human must declare the artefact path via the supplement form.
                </p>
              </div>
            </div>
          )}

          {/* Explanation */}
          {finding.explanation && (
            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Explanation</h4>
              <p className="text-sm text-gray-700 leading-relaxed">{finding.explanation}</p>
            </div>
          )}

          {/* Remediation steps */}
          {steps && steps.length > 0 && outcome !== "pass" && (
            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Remediation Steps</h4>
              <ol className="space-y-3">
                {steps.map((step, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 text-xs font-bold flex items-center justify-center">
                      {step.step_number ?? i + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800">{step.action}</p>
                      {step.artifact_to_produce && (
                        <p className="text-xs text-gray-500 mt-0.5">
                          Produce: <span className="font-mono text-gray-700">{step.artifact_to_produce}</span>
                        </p>
                      )}
                      {step.example_approach && (
                        <p className="text-xs text-gray-500 mt-1 leading-relaxed italic">{step.example_approach}</p>
                      )}
                      {step.priority && (
                        <span className={`inline-block mt-1.5 text-xs px-2 py-0.5 rounded border font-medium ${PRIORITY_COLORS[step.priority] ?? "bg-gray-50 text-gray-500 border-gray-200"}`}>
                          {step.priority.replace(/_/g, " ")}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Raw remediation fallback (if not parseable) */}
          {!steps && finding.remediation && outcome !== "pass" && (
            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Remediation</h4>
              <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">{finding.remediation}</p>
            </div>
          )}

          {/* Evidence paths */}
          {evidencePaths.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Evidence Found</h4>
              <div className="flex flex-wrap gap-1.5">
                {evidencePaths.map((p) => (
                  <span key={p} className="text-xs font-mono bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-1 rounded-lg">
                    {p}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

type Filter = "all" | "pass" | "partial" | "missing" | "not_evaluable";

const FILTER_TABS: { key: Filter; label: string; color: string; activeColor: string }[] = [
  { key: "all",          label: "All",       color: "text-gray-600 border-transparent",      activeColor: "text-gray-900 border-gray-900 font-semibold" },
  { key: "pass",         label: "Pass",      color: "text-emerald-600 border-transparent",   activeColor: "text-emerald-700 border-emerald-600 font-semibold" },
  { key: "partial",      label: "Partial",   color: "text-amber-600 border-transparent",     activeColor: "text-amber-700 border-amber-600 font-semibold" },
  { key: "missing",      label: "Missing",   color: "text-red-600 border-transparent",       activeColor: "text-red-700 border-red-600 font-semibold" },
  { key: "not_evaluable",label: "Supplement",color: "text-purple-600 border-transparent",    activeColor: "text-purple-700 border-purple-600 font-semibold" },
];

export default function ReportPageClient() {
  const params = useParams();
  const scanId = params.scanId as string;
  const [filter, setFilter] = useState<Filter>("all");

  const { data: findings = [], isLoading, isError } = useQuery({
    queryKey: ["findings", scanId],
    queryFn: () => apiClient.getFindings(scanId),
    enabled: !!scanId,
  });

  const normalise = (o: string) => o.toLowerCase();

  const counts = {
    all:          findings.length,
    pass:         findings.filter((f) => normalise(f.outcome) === "pass").length,
    partial:      findings.filter((f) => normalise(f.outcome) === "partial").length,
    missing:      findings.filter((f) => normalise(f.outcome) === "missing").length,
    not_evaluable:findings.filter((f) => normalise(f.outcome) === "not_evaluable").length,
  };

  const filtered = filter === "all"
    ? findings
    : findings.filter((f) => normalise(f.outcome) === filter);

  const grouped = filtered.reduce<Record<string, ControlResultRead[]>>((acc, f) => {
    const p = getPillar(f.control_id);
    (acc[p] ??= []).push(f);
    return acc;
  }, {});

  const passRate = counts.all > 0 ? Math.round((counts.pass / counts.all) * 100) : 0;

  if (isLoading) return (
    <div className="max-w-3xl mx-auto text-center py-20">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
      <p className="text-gray-500 text-sm">Loading report…</p>
    </div>
  );
  if (isError) return (
    <div className="max-w-3xl mx-auto text-center py-20">
      <p className="text-red-600 font-medium">Failed to load report.</p>
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Ethics Review Report</h1>
        <p className="text-xs text-gray-400 font-mono mt-1 break-all">Scan ID: {scanId}</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "Total",      value: counts.all,          bg: "bg-gray-50  border-gray-200",   text: "text-gray-800" },
          { label: "Pass",       value: counts.pass,         bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700" },
          { label: "Partial",    value: counts.partial,      bg: "bg-amber-50 border-amber-200",  text: "text-amber-700" },
          { label: "Missing",    value: counts.missing,      bg: "bg-red-50   border-red-200",    text: "text-red-700" },
        ].map(({ label, value, bg, text }) => (
          <div key={label} className={`rounded-xl border p-4 text-center ${bg}`}>
            <p className={`text-3xl font-bold ${text}`}>{value}</p>
            <p className={`text-xs font-medium mt-0.5 ${text} opacity-80`}>{label}</p>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      {counts.all > 0 && (
        <div className="mb-6">
          <div className="h-2 rounded-full overflow-hidden bg-gray-100 flex gap-0.5">
            <div className="bg-emerald-500 transition-all" style={{ width: `${(counts.pass / counts.all) * 100}%` }} />
            <div className="bg-amber-400 transition-all"  style={{ width: `${(counts.partial / counts.all) * 100}%` }} />
            <div className="bg-red-400 transition-all"    style={{ width: `${(counts.missing / counts.all) * 100}%` }} />
            <div className="bg-purple-300 transition-all" style={{ width: `${(counts.not_evaluable / counts.all) * 100}%` }} />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1.5">
            <span className="text-emerald-600 font-medium">{passRate}% pass</span>
            <span>{counts.not_evaluable} supplement required</span>
          </div>
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex gap-1 border-b border-gray-200 mb-6 overflow-x-auto">
        {FILTER_TABS.map(({ key, label, color, activeColor }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 -mb-px transition-all whitespace-nowrap ${
              filter === key ? activeColor : `${color} hover:text-gray-700`
            }`}
          >
            {label}
            <span className={`text-xs rounded-full px-1.5 py-0.5 font-medium ${
              filter === key ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-500"
            }`}>{counts[key]}</span>
          </button>
        ))}
        {filter !== "all" && (
          <button onClick={() => setFilter("all")} className="ml-auto text-xs text-gray-400 hover:text-gray-600 px-2 whitespace-nowrap">
            Clear ×
          </button>
        )}
      </div>

      {/* Findings grouped by pillar */}
      {filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-sm">No controls match this filter.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {Object.entries(grouped)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([pillar, items]) => (
              <div key={pillar}>
                <div className="flex items-center gap-3 mb-3">
                  <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest whitespace-nowrap">{pillar}</h2>
                  <span className="text-xs text-gray-300 font-medium flex-shrink-0">{items.length}</span>
                  <div className="flex-1 h-px bg-gray-100" />
                </div>
                <div className="space-y-2">
                  {items.map((finding) => (
                    <FindingCard key={finding.control_id} finding={finding} />
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
