"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";

const STAGES = [
  { id: "S1_INTAKE",    label: "S1 Intake",    description: "Validate registry and accept repository" },
  { id: "S2_MANIFEST",  label: "S2 Manifest",  description: "Download repo and build file manifest" },
  { id: "S3_AI_DETECT", label: "S3 AI Detect", description: "Scan imports and detect AI signals" },
  { id: "S4_FILTER",    label: "S4 Filter",    description: "Activate controls by project profile" },
  { id: "S5_RUNNER",    label: "S5 Runner",    description: "Run all plugins in parallel" },
  { id: "S6_TAG",       label: "S6 Tag",       description: "Route GEN/REL overlay findings" },
  { id: "S7_EVIDENCE",  label: "S7 Evidence",  description: "Map findings to outcomes" },
  { id: "S8_HONESTY",   label: "S8 Honesty",   description: "Compare declared vs detected profile" },
  { id: "S9_LLM",       label: "S9 LLM",       description: "Generate explanations and remediation" },
  { id: "S10_ASSEMBLE", label: "S10 Assemble", description: "Build output packages" },
  { id: "S11_AUDIT",    label: "S11 Audit",    description: "Seal immutable audit record" },
];

const STAGE_ORDER = STAGES.map((s) => s.id);
type StageStatus = "complete" | "active" | "pending" | "failed";

function getStageStatus(stageId: string, currentStatus: string): StageStatus {
  if (currentStatus === "COMPLETE") return "complete";
  if (currentStatus === "FAILED") {
    const idx = STAGE_ORDER.indexOf(stageId);
    const cur = STAGE_ORDER.indexOf(currentStatus);
    return idx < cur ? "complete" : "failed";
  }
  const idx = STAGE_ORDER.indexOf(stageId);
  const cur = STAGE_ORDER.indexOf(currentStatus);
  if (idx < cur) return "complete";
  if (idx === cur) return "active";
  return "pending";
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

function StageRow({ stage, status, duration, isLast }: {
  stage: (typeof STAGES)[0];
  status: StageStatus;
  duration?: number;
  isLast: boolean;
}) {
  const iconBg: Record<StageStatus, string> = {
    complete: "bg-emerald-500 border-emerald-500 text-white",
    active:   "bg-blue-500 border-blue-500 text-white animate-pulse",
    pending:  "bg-white border-gray-200 text-gray-300",
    failed:   "bg-red-500 border-red-500 text-white",
  };
  const labelColor: Record<StageStatus, string> = {
    complete: "text-gray-900 font-semibold",
    active:   "text-blue-700 font-semibold",
    pending:  "text-gray-400",
    failed:   "text-red-700 font-semibold",
  };
  const descColor: Record<StageStatus, string> = {
    complete: "text-gray-500",
    active:   "text-blue-500",
    pending:  "text-gray-300",
    failed:   "text-red-400",
  };

  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className={`w-9 h-9 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-sm font-bold ${iconBg[status]}`}>
          {status === "complete" ? (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : status === "active" ? (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
          ) : status === "failed" ? "✕" : (
            <span className="text-xs text-gray-300">{stage.label.replace(/S\d+ /, "").slice(0, 2)}</span>
          )}
        </div>
        {!isLast && (
          <div className={`w-0.5 my-1 flex-1 ${status === "complete" ? "bg-emerald-200" : "bg-gray-100"}`} style={{ minHeight: "1.25rem" }} />
        )}
      </div>
      <div className={`pb-5 flex-1 ${isLast ? "pb-1" : ""}`}>
        <div className="flex items-center justify-between gap-2">
          <span className={`text-sm ${labelColor[status]}`}>{stage.label}</span>
          {duration != null && status === "complete" && (
            <span className="text-xs font-mono text-gray-400 bg-gray-50 border border-gray-100 px-2 py-0.5 rounded-full">
              {formatDuration(duration)}
            </span>
          )}
          {status === "active" && (
            <span className="text-xs text-blue-500 animate-pulse font-medium">running…</span>
          )}
        </div>
        <p className={`text-xs mt-0.5 ${descColor[status]}`}>{stage.description}</p>
      </div>
    </div>
  );
}

export default function ScanPageClient() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.scanId as string;

  const { data: scan, isError } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => apiClient.getScan(scanId),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      if (!s || s === "COMPLETE" || s === "FAILED") return false;
      return 2000;
    },
    enabled: !!scanId,
  });

  const { data: auditLog } = useQuery({
    queryKey: ["audit", scanId],
    queryFn: () => apiClient.getAuditLog(scanId),
    refetchInterval: () => {
      const s = scan?.status;
      if (!s || s === "COMPLETE" || s === "FAILED") return false;
      return 3000;
    },
    enabled: !!scanId,
  });

  const timings: Record<string, number> = {};
  let totalDuration: number | undefined;
  if (auditLog) {
    for (const entry of auditLog) {
      const d = entry.payload?.duration_s;
      if (typeof d === "number") timings[entry.stage] = d;
      const tot = entry.payload?.total_duration_s;
      if (typeof tot === "number") totalDuration = tot;
    }
  }

  if (isError) return (
    <div className="max-w-lg mx-auto text-center py-16">
      <p className="text-red-600 font-medium">Failed to load scan.</p>
    </div>
  );

  const currentStatus = scan?.status ?? "PENDING";
  const isComplete = currentStatus === "COMPLETE";
  const isFailed   = currentStatus === "FAILED";
  const completedCount = STAGES.filter((s) =>
    isComplete ? true : STAGE_ORDER.indexOf(s.id) < STAGE_ORDER.indexOf(currentStatus)
  ).length;

  return (
    <div className="max-w-xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Scan Progress</h1>
            <p className="text-xs text-gray-400 font-mono mt-1 break-all">{scanId}</p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            {totalDuration != null && (
              <span className="text-sm text-gray-500">
                Total: <span className="font-semibold text-gray-700">{formatDuration(totalDuration)}</span>
              </span>
            )}
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border ${
              isComplete ? "bg-emerald-50 text-emerald-700 border-emerald-200"
              : isFailed  ? "bg-red-50 text-red-700 border-red-200"
              : "bg-blue-50 text-blue-700 border-blue-200"
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isComplete ? "bg-emerald-500" : isFailed ? "bg-red-500" : "bg-blue-500 animate-pulse"}`} />
              {isComplete ? "Complete" : isFailed ? "Failed" : currentStatus === "PENDING" ? "Queued" : "Running"}
            </span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="flex justify-between text-xs text-gray-400 mb-1.5">
            <span>{completedCount} / {STAGES.length} stages</span>
            <span>{Math.round((completedCount / STAGES.length) * 100)}%</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${isComplete ? "bg-emerald-500" : isFailed ? "bg-red-500" : "bg-blue-500"}`}
              style={{ width: `${(completedCount / STAGES.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stages */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm px-6 pt-6 pb-4">
        {STAGES.map((stage, i) => (
          <StageRow
            key={stage.id}
            stage={stage}
            status={
              isComplete ? "complete"
              : currentStatus === "PENDING" ? "pending"
              : getStageStatus(stage.id, currentStatus)
            }
            duration={timings[stage.id]}
            isLast={i === STAGES.length - 1}
          />
        ))}
      </div>

      {/* CTA */}
      {isComplete && (
        <button
          onClick={() => router.push(`/report/${scanId}`)}
          className="mt-5 w-full py-3 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-colors shadow-sm text-sm"
        >
          View Report →
        </button>
      )}
      {isFailed && (
        <div className="mt-5 p-4 bg-red-50 border border-red-100 rounded-xl">
          <p className="text-sm font-semibold text-red-700 mb-3">The scan failed. Check the audit log for details.</p>
          <button
            onClick={() => router.push(`/audit/${scanId}`)}
            className="w-full py-2.5 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            View Audit Log →
          </button>
        </div>
      )}
    </div>
  );
}
