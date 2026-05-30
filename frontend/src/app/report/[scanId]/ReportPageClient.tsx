"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient, type ControlResultRead } from "@/lib/api";

// Outcome styles — lowercase values from the new pipeline
const OUTCOME_CONFIG: Record<string, { label: string; badge: string; row: string }> = {
  evidence_found: { label: "Pass",          badge: "bg-emerald-100 text-emerald-700 border-emerald-200", row: "" },
  pass:           { label: "Pass",          badge: "bg-emerald-100 text-emerald-700 border-emerald-200", row: "" },
  partial:        { label: "Partial",       badge: "bg-amber-100 text-amber-700 border-amber-200",      row: "" },
  missing:        { label: "Missing",       badge: "bg-red-100 text-red-700 border-red-200",            row: "bg-red-50/30" },
  not_evaluable:  { label: "Supplement",    badge: "bg-purple-100 text-purple-700 border-purple-200",   row: "bg-purple-50/20" },
  not_triggered:  { label: "Not triggered", badge: "bg-gray-100 text-gray-500 border-gray-200",         row: "" },
  error:          { label: "Error",         badge: "bg-orange-100 text-orange-700 border-orange-200",   row: "" },
  // Legacy uppercase fallbacks
  PASS:           { label: "Pass",          badge: "bg-emerald-100 text-emerald-700 border-emerald-200", row: "" },
  PARTIAL:        { label: "Partial",       badge: "bg-amber-100 text-amber-700 border-amber-200",      row: "" },
  MISSING:        { label: "Missing",       badge: "bg-red-100 text-red-700 border-red-200",            row: "bg-red-50/30" },
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

const isPass = (o: string) => o === "pass" || o === "evidence_found";

type RemediationStep = {
  step_number?: number;
  action?: string;
  artifact_to_produce?: string;
  example_approach?: string;
  priority?: string;
};

function parseRemediation(raw: string | null | undefined): RemediationStep[] | null {
  if (!raw) return null;

  // 1. Try clean JSON parse first (new format from backend)
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed;
    if (parsed?.remediation_steps) return parsed.remediation_steps;
  } catch {}

  // 2. Python repr with apostrophes in values — extract each step with regex
  // Matches: {'step_number': N, 'action': '...', 'artifact_to_produce': '...', ...}
  try {
    const steps: RemediationStep[] = [];
    // Split on dict boundaries: look for }, { pattern
    const dictPattern = /\{[^{}]+\}/g;
    const matches = raw.match(dictPattern);
    if (matches) {
      for (const dictStr of matches) {
        const step: RemediationStep = {};
        // Extract each key-value pair carefully
        const kvPattern = /'(\w+)':\s*(?:'((?:[^'\\]|\\.|'')*)'|(\d+))/g;
        let m: RegExpExecArray | null;
        while ((m = kvPattern.exec(dictStr)) !== null) {
          const key = m[1];
          const val = m[2] !== undefined ? m[2] : m[3] !== undefined ? parseInt(m[3]) : "";
          (step as Record<string, unknown>)[key] = val;
        }
        if (step.action) steps.push(step);
      }
      if (steps.length > 0) return steps;
    }
  } catch {}

  return null;
}

const PRIORITY_COLORS: Record<string, string> = {
  immediate:        "bg-red-50 text-red-700 border-red-200",
  before_reviewer:  "bg-amber-50 text-amber-700 border-amber-200",
  before_certifier: "bg-blue-50 text-blue-700 border-blue-200",
};

function FindingCard({ finding, scanId }: { finding: ControlResultRead; scanId: string }) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [showDeterministic, setShowDeterministic] = useState(false);
  const outcome = (finding.outcome ?? "").toLowerCase();
  const cfg = OUTCOME_CONFIG[finding.outcome] ?? OUTCOME_CONFIG[outcome] ?? {
    label: finding.outcome, badge: "bg-gray-100 text-gray-600 border-gray-200", row: "",
  };
  const steps = parseRemediation(finding.remediation);
  const evidencePaths: string[] = (finding.evidence as { paths?: string[] } | null)?.paths ?? [];
  const isNotEvaluable = outcome === "not_evaluable";
  const hasDetExp = !!finding.deterministic_explanation;

  // LLM scanner data
  const llmOutcome = finding.llm_outcome ?? null;
  const llmCfg = llmOutcome ? (OUTCOME_CONFIG[llmOutcome] ?? { label: llmOutcome, badge: "bg-gray-100 text-gray-600 border-gray-200", row: "" }) : null;
  const llmSelectedFiles: string[] = (finding.llm_evidence as { selected_files?: string[] } | null)?.selected_files ?? [];
  const llmQuotes: string[] = (finding.llm_evidence as { quotes?: string[] } | null)?.quotes ?? [];
  const llmConfidencePct = finding.llm_confidence != null ? Math.round(finding.llm_confidence * 100) : null;
  const llmDisagrees = llmOutcome && llmOutcome !== "error" && llmOutcome !== outcome && llmOutcome !== finding.outcome;

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
          {/* Not evaluable notice — T3 controls only */}
          {isNotEvaluable && (
            <div className="flex items-start justify-between gap-3 p-3 bg-purple-50 border border-purple-100 rounded-lg">
              <div className="flex gap-3">
                <span className="text-purple-500 text-lg leading-none flex-shrink-0">📋</span>
                <div>
                  <p className="text-sm font-semibold text-purple-800">Design-only control — supplement required</p>
                  <p className="text-xs text-purple-600 mt-0.5">
                    This control cannot be assessed from code alone. Declare the artefact path via the supplement form.
                  </p>
                </div>
              </div>
              <button
                onClick={() => router.push(`/supplement/${scanId}`)}
                className="flex-shrink-0 text-xs font-semibold px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                Fill in →
              </button>
            </div>
          )}

          {/* Explanation toggle — only shown for T1 controls */}
          {hasDetExp && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-400 uppercase tracking-widest font-bold">Explanation</span>
              <div className="flex items-center gap-1 ml-auto bg-gray-100 rounded-lg p-0.5">
                <button
                  onClick={() => setShowDeterministic(false)}
                  className={`text-xs px-2.5 py-1 rounded-md font-medium transition-all ${
                    !showDeterministic
                      ? "bg-white text-blue-700 shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  LLM
                </button>
                <button
                  onClick={() => setShowDeterministic(true)}
                  className={`text-xs px-2.5 py-1 rounded-md font-medium transition-all ${
                    showDeterministic
                      ? "bg-white text-emerald-700 shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  Scanner
                </button>
              </div>
            </div>
          )}

          {/* Explanation content */}
          {!hasDetExp && finding.explanation && (
            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Explanation</h4>
              <p className="text-sm text-gray-700 leading-relaxed">{finding.explanation}</p>
            </div>
          )}
          {hasDetExp && !showDeterministic && finding.explanation && (
            <p className="text-sm text-gray-700 leading-relaxed">{finding.explanation}</p>
          )}
          {hasDetExp && showDeterministic && (
            <p className="text-sm text-emerald-800 leading-relaxed font-mono bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">
              {finding.deterministic_explanation}
            </p>
          )}

          {/* Remediation steps */}
          {steps && steps.length > 0 && !isPass(outcome) && (
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
          {!steps && finding.remediation && !isPass(outcome) && (
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

          {/* Scanner comparison panel */}
          <div>
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Scanner Comparison</h4>
            <div className="grid grid-cols-2 gap-3">
              {/* Keyword scanner column */}
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-gray-500">Keyword</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${cfg.badge}`}>
                    {cfg.label}
                  </span>
                </div>
                {evidencePaths.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {evidencePaths.map((p) => (
                      <span key={p} className="text-xs font-mono bg-white border border-gray-200 text-gray-600 px-1.5 py-0.5 rounded">
                        {p.split("/").pop()}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">No matching files found</p>
                )}
              </div>

              {/* LLM scanner column */}
              <div className="rounded-lg border border-blue-200 bg-blue-50/40 p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-blue-600">LLM</span>
                  {llmCfg ? (
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-semibold ${llmCfg.badge}`}>
                        {llmCfg.label}
                      </span>
                      {llmConfidencePct != null && (
                        <span className="text-xs text-blue-500 font-mono">{llmConfidencePct}%</span>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-gray-400">Not run</span>
                  )}
                </div>
                {finding.llm_reasoning && (
                  <p className="text-xs text-gray-700 leading-relaxed mb-2">{finding.llm_reasoning}</p>
                )}
                {llmSelectedFiles.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {llmSelectedFiles.map((p) => (
                      <span key={p} className="text-xs font-mono bg-white border border-blue-200 text-blue-700 px-1.5 py-0.5 rounded">
                        {p.split("/").pop()}
                      </span>
                    ))}
                  </div>
                )}
                {llmQuotes.length > 0 && (
                  <div className="space-y-1">
                    {llmQuotes.map((q, i) => (
                      <blockquote key={i} className="text-xs text-blue-800 bg-white border-l-2 border-blue-300 pl-2 py-0.5 italic leading-relaxed">
                        &ldquo;{q}&rdquo;
                      </blockquote>
                    ))}
                  </div>
                )}
                {!llmCfg && (
                  <p className="text-xs text-gray-400 italic">Configure an API key to enable LLM scanning</p>
                )}
              </div>
            </div>

            {/* Disagreement banner */}
            {llmDisagrees && llmCfg && (
              <div className="mt-2 flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                </svg>
                <span>
                  Keyword scanner: <strong>{cfg.label}</strong> — LLM: <strong>{llmCfg.label}</strong>. Review both results manually.
                </span>
              </div>
            )}
          </div>
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
  const router = useRouter();
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
    pass:         findings.filter((f) => isPass(normalise(f.outcome))).length,
    partial:      findings.filter((f) => normalise(f.outcome) === "partial").length,
    missing:      findings.filter((f) => normalise(f.outcome) === "missing").length,
    not_evaluable:findings.filter((f) => normalise(f.outcome) === "not_evaluable").length,
  };

  const filtered = filter === "all"
    ? findings
    : filter === "pass"
      ? findings.filter((f) => isPass(normalise(f.outcome)))
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

      {/* Supplement action banner */}
      {counts.not_evaluable > 0 && (
        <div className="mb-6 p-4 bg-purple-50 border border-purple-200 rounded-xl flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-sm font-semibold text-purple-800">
              {counts.not_evaluable} control{counts.not_evaluable !== 1 ? "s" : ""} need your input
            </p>
            <p className="text-xs text-purple-600 mt-0.5">
              Declare artefact paths for design-only controls to complete the review.
            </p>
          </div>
          <button
            onClick={() => router.push(`/supplement/${scanId}`)}
            className="flex-shrink-0 px-4 py-2 bg-purple-600 text-white text-sm font-semibold rounded-lg hover:bg-purple-700 transition-colors"
          >
            Fill in now →
          </button>
        </div>
      )}

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
                    <FindingCard key={finding.control_id} finding={finding} scanId={scanId} />
                  ))}
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
