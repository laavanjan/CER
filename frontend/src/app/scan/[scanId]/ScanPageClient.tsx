"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";

const STAGES = [
  { id: "S1_INTAKE",    label: "S1 Intake",    description: "Validate registry, accept repository" },
  { id: "S2_MANIFEST",  label: "S2 Manifest",  description: "Clone repo, build file manifest" },
  { id: "S3_AI_DETECT", label: "S3 AI Detect", description: "Scan imports, detect AI signals" },
  { id: "S4_FILTER",    label: "S4 Filter",    description: "Filter controls by project profile" },
  { id: "S5_RUNNER",    label: "S5 Runner",    description: "Parallel plugin runner" },
  { id: "S6_TAG",       label: "S6 Tag",       description: "Tag GEN/REL overlay findings" },
  { id: "S7_EVIDENCE",  label: "S7 Evidence",  description: "Map findings to PASS/PARTIAL/MISSING" },
  { id: "S8_HONESTY",   label: "S8 Honesty",   description: "Compare declared vs detected profile" },
  { id: "S9_LLM",       label: "S9 LLM",       description: "Generate explanations and remediation" },
  { id: "S10_ASSEMBLE", label: "S10 Assemble", description: "Assemble output packages" },
  { id: "S11_AUDIT",    label: "S11 Audit",    description: "Write audit log (WORM)" },
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
  const s = (seconds % 60).toFixed(0);
  return `${m}m ${s}s`;
}

function StageIndicator({
  stage,
  status,
  duration,
}: {
  stage: (typeof STAGES)[0];
  status: StageStatus;
  duration?: number;
}) {
  const colors: Record<StageStatus, string> = {
    complete: "bg-green-500 text-white",
    active:   "bg-blue-500 text-white animate-pulse",
    pending:  "bg-gray-200 text-gray-500",
    failed:   "bg-red-500 text-white",
  };

  return (
    <div className="flex items-start gap-3">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${colors[status]}`}>
        {status === "complete" ? "✓" : stage.label.split(" ")[0]}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-medium text-gray-900">{stage.label}</p>
          {duration != null && status === "complete" && (
            <span className="text-xs font-mono text-gray-400 whitespace-nowrap">{formatDuration(duration)}</span>
          )}
          {status === "active" && (
            <span className="text-xs text-blue-500 animate-pulse whitespace-nowrap">running…</span>
          )}
        </div>
        <p className="text-xs text-gray-500">{stage.description}</p>
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
      const status = query.state.data?.status;
      if (!status || status === "COMPLETE" || status === "FAILED") return false;
      return 2000;
    },
    enabled: !!scanId,
  });

  const { data: auditLog } = useQuery({
    queryKey: ["audit", scanId],
    queryFn: () => apiClient.getAuditLog(scanId),
    refetchInterval: (query) => {
      const status = scan?.status;
      if (!status || status === "COMPLETE" || status === "FAILED") return false;
      return 3000;
    },
    enabled: !!scanId,
  });

  // Build a map of stage -> duration_s from audit log
  const timings: Record<string, number> = {};
  let totalDuration: number | undefined;
  if (auditLog) {
    for (const entry of auditLog) {
      const d = entry.payload?.duration_s;
      if (typeof d === "number") timings[entry.stage] = d;
      const total = entry.payload?.total_duration_s;
      if (typeof total === "number") totalDuration = total;
    }
  }

  if (isError) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <p className="text-red-600">Failed to load scan. Please try again.</p>
      </div>
    );
  }

  const currentStatus = scan?.status ?? "PENDING";

  return (
    <div className="max-w-lg mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Scan Progress</h1>
        <p className="text-sm text-gray-500">Scan ID: {scanId}</p>
      </div>

      <div className="mb-6 flex items-center gap-4">
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
          currentStatus === "COMPLETE" ? "bg-green-100 text-green-800"
          : currentStatus === "FAILED"  ? "bg-red-100 text-red-800"
          : "bg-blue-100 text-blue-800"
        }`}>
          {currentStatus === "PENDING" ? "Queued" : currentStatus.replace("_", " ")}
        </span>
        {totalDuration != null && (
          <span className="text-sm text-gray-500">
            Total: <span className="font-mono font-medium text-gray-700">{formatDuration(totalDuration)}</span>
          </span>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
        {STAGES.map((stage) => (
          <StageIndicator
            key={stage.id}
            stage={stage}
            status={
              currentStatus === "COMPLETE" ? "complete"
              : currentStatus === "PENDING" ? "pending"
              : getStageStatus(stage.id, currentStatus)
            }
            duration={timings[stage.id]}
          />
        ))}
      </div>

      {currentStatus === "COMPLETE" && (
        <div className="mt-6 text-center">
          <button
            onClick={() => router.push(`/report/${scanId}`)}
            className="px-6 py-3 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
          >
            View Report →
          </button>
        </div>
      )}

      {currentStatus === "FAILED" && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm space-y-3">
          <p className="font-medium">The scan failed. Check the audit log for details.</p>
          <button
            onClick={() => router.push(`/audit/${scanId}`)}
            className="inline-flex items-center px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            View Audit Log →
          </button>
        </div>
      )}
    </div>
  );
}
