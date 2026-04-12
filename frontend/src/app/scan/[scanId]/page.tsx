"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";

// Required for Next.js static export — scan IDs are not known at build time.
// The FastAPI SPA fallback serves index.html for unknown paths so the client-
// side router handles the route dynamically.
export function generateStaticParams() {
  return [];
}

// Pipeline stage definitions in order S1–S11
const STAGES = [
  { id: "S1_INTAKE", label: "S1 Intake", description: "Validate registry, accept repository" },
  { id: "S2_MANIFEST", label: "S2 Manifest", description: "Clone repo, build file manifest" },
  { id: "S3_AI_DETECT", label: "S3 AI Detect", description: "Scan imports, detect AI signals" },
  { id: "S4_FILTER", label: "S4 Filter", description: "Filter controls by project profile" },
  { id: "S5_RUNNER", label: "S5 Runner", description: "Parallel plugin runner" },
  { id: "S6_TAG", label: "S6 Tag", description: "Tag GEN/REL overlay findings" },
  { id: "S7_EVIDENCE", label: "S7 Evidence", description: "Map findings to PASS/PARTIAL/MISSING" },
  { id: "S8_HONESTY", label: "S8 Honesty", description: "Compare declared vs detected profile" },
  { id: "S9_LLM", label: "S9 LLM", description: "Generate explanations and remediation" },
  { id: "S10_ASSEMBLE", label: "S10 Assemble", description: "Assemble output packages" },
  { id: "S11_AUDIT", label: "S11 Audit", description: "Write audit log (WORM)" },
];

const STAGE_ORDER = STAGES.map((s) => s.id);

function getStageIndex(status: string): number {
  return STAGE_ORDER.indexOf(status);
}

type StageStatus = "complete" | "active" | "pending" | "failed";

function getStageStatus(stageId: string, currentStatus: string): StageStatus {
  if (currentStatus === "FAILED") {
    const idx = getStageIndex(stageId);
    const cur = getStageIndex(currentStatus);
    if (idx < cur) return "complete";
    return "failed";
  }
  if (currentStatus === "COMPLETE") return "complete";
  const idx = getStageIndex(stageId);
  const cur = getStageIndex(currentStatus);
  if (idx < cur) return "complete";
  if (idx === cur) return "active";
  return "pending";
}

function StageIndicator({
  stage,
  status,
}: {
  stage: (typeof STAGES)[0];
  status: StageStatus;
}) {
  const colors: Record<StageStatus, string> = {
    complete: "bg-green-500 text-white",
    active: "bg-blue-500 text-white animate-pulse",
    pending: "bg-gray-200 text-gray-500",
    failed: "bg-red-500 text-white",
  };

  return (
    <div className="flex items-start gap-3">
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${colors[status]}`}
      >
        {status === "complete" ? "✓" : stage.label.split(" ")[0]}
      </div>
      <div>
        <p className="text-sm font-medium text-gray-900">{stage.label}</p>
        <p className="text-xs text-gray-500">{stage.description}</p>
      </div>
    </div>
  );
}

export default function ScanPage() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.scanId as string;

  const { data: scan, isError } = useQuery({
    queryKey: ["scan", scanId],
    queryFn: () => apiClient.getScan(scanId),
    // Poll every 2 seconds while not complete
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || status === "COMPLETE" || status === "FAILED") return false;
      return 2000;
    },
    enabled: !!scanId,
  });

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

      {/* Overall status badge */}
      <div className="mb-6">
        <span
          className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            currentStatus === "COMPLETE"
              ? "bg-green-100 text-green-800"
              : currentStatus === "FAILED"
              ? "bg-red-100 text-red-800"
              : "bg-blue-100 text-blue-800"
          }`}
        >
          {currentStatus === "PENDING" ? "Queued" : currentStatus.replace("_", " ")}
        </span>
      </div>

      {/* Stage list */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 space-y-4">
        {STAGES.map((stage) => (
          <StageIndicator
            key={stage.id}
            stage={stage}
            status={
              currentStatus === "COMPLETE"
                ? "complete"
                : currentStatus === "PENDING"
                ? "pending"
                : getStageStatus(stage.id, currentStatus)
            }
          />
        ))}
      </div>

      {/* Actions */}
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
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
          The scan failed. Please check the audit log or try again.
        </div>
      )}
    </div>
  );
}
