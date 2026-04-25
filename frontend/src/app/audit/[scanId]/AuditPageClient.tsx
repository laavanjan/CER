"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient, type AuditLogRead } from "@/lib/api";

const EVENT_STYLES: Record<string, { bg: string; text: string; dot: string; label: string }> = {
  started:   { bg: "bg-blue-50",   text: "text-blue-800",   dot: "bg-blue-500",   label: "Started"   },
  completed: { bg: "bg-green-50",  text: "text-green-800",  dot: "bg-green-500",  label: "Completed" },
  failed:    { bg: "bg-red-50",    text: "text-red-800",    dot: "bg-red-500",    label: "Failed"    },
  skipped:   { bg: "bg-gray-50",   text: "text-gray-600",   dot: "bg-gray-400",   label: "Skipped"   },
};

function getEventStyle(event: string) {
  const key = Object.keys(EVENT_STYLES).find((k) => event.toLowerCase().includes(k));
  return EVENT_STYLES[key ?? ""] ?? {
    bg: "bg-yellow-50", text: "text-yellow-800", dot: "bg-yellow-500", label: event,
  };
}

function AuditEntry({ entry }: { entry: AuditLogRead }) {
  const style = getEventStyle(entry.event);
  const time = new Date(entry.recorded_at).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
  const date = new Date(entry.recorded_at).toLocaleDateString();

  return (
    <div className={`rounded-lg border p-4 ${style.bg}`}>
      <div className="flex items-start justify-between gap-4">
        {/* Left: stage + event */}
        <div className="flex items-center gap-3 min-w-0">
          <span className={`flex-shrink-0 w-2.5 h-2.5 rounded-full mt-1 ${style.dot}`} />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono font-bold text-sm text-gray-800">{entry.stage}</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${style.bg} ${style.text} border border-current/20`}>
                {entry.event}
              </span>
            </div>
            {/* Payload — show error/message if present */}
            {entry.payload && Object.keys(entry.payload).length > 0 && (
              <div className="mt-2 text-xs text-gray-700 bg-white/70 rounded p-2 border border-gray-200 font-mono whitespace-pre-wrap break-all">
                {entry.payload.error
                  ? String(entry.payload.error)
                  : JSON.stringify(entry.payload, null, 2)}
              </div>
            )}
          </div>
        </div>
        {/* Right: timestamp */}
        <div className="flex-shrink-0 text-right text-xs text-gray-500">
          <p>{time}</p>
          <p>{date}</p>
        </div>
      </div>
    </div>
  );
}

export default function AuditPageClient() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.scanId as string;

  const { data: logs = [], isLoading, isError } = useQuery({
    queryKey: ["audit", scanId],
    queryFn: () => apiClient.getAuditLog(scanId),
    enabled: !!scanId,
  });

  const failedEntry = logs.find((l) => l.event.toLowerCase().includes("failed"));

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-500 hover:text-gray-800 mb-4 flex items-center gap-1"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        <p className="text-sm text-gray-500 font-mono mt-1">{scanId}</p>
      </div>

      {/* Failure summary banner */}
      {failedEntry && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm font-semibold text-red-800 mb-1">
            Pipeline failed at stage: <span className="font-mono">{failedEntry.stage}</span>
          </p>
          {failedEntry.payload?.error != null && (
            <p className="text-xs text-red-700 font-mono whitespace-pre-wrap break-all">
              {String(failedEntry.payload.error)}
            </p>
          )}
        </div>
      )}

      {/* Log entries */}
      {isLoading ? (
        <div className="text-center py-16 text-gray-400">Loading audit log…</div>
      ) : isError ? (
        <div className="text-center py-16 text-red-600">Failed to load audit log.</div>
      ) : logs.length === 0 ? (
        <div className="text-center py-16 text-gray-400">No audit entries found for this scan.</div>
      ) : (
        <div className="space-y-3">
          {logs.map((entry) => (
            <AuditEntry key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
