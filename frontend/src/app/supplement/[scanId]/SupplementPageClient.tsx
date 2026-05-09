"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { apiClient, type SupplementRead } from "@/lib/api";

const PILLAR_MAP: Record<string, string> = {
  ACC:  "Accessibility, Inclusion & Human Factors",
  DOC:  "Documentation & Traceability",
  FAIR: "Fairness & Non-Discrimination",
  GOV:  "Governance & Accountability",
  HUMO: "Human Oversight & Recourse",
  PRIV: "Data Governance & Privacy",
  SAFE: "Safety & Robustness",
  SEC:  "Security & Misuse Prevention",
  TRAN: "Transparency & Explainability",
  GEN:  "Generative AI Overlay",
  REL:  "Reliability AI Overlay",
};

function getPillar(controlId: string): string {
  const prefix = controlId.split("-")[0];
  return PILLAR_MAP[prefix] ?? prefix;
}

function StatusBadge({ status }: { status: string }) {
  if (status === "partial") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 border border-amber-200">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        Declared
      </span>
    );
  }
  if (status === "missing") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700 border border-red-200">
        <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
        No artefact
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 border border-purple-200">
      <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
      Pending
    </span>
  );
}

function SupplementCard({
  entry,
  value,
  onChange,
  submitted,
}: {
  entry: SupplementRead;
  value: string;
  onChange: (val: string) => void;
  submitted: boolean;
}) {
  const status = submitted
    ? value.trim() ? "partial" : "missing"
    : entry.status_after_supplement;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-sm font-bold text-gray-800">{entry.control_id}</span>
          <span className="text-xs text-gray-400">{getPillar(entry.control_id)}</span>
        </div>
        <StatusBadge status={status} />
      </div>

      <p className="text-sm text-gray-700 leading-relaxed">{entry.supplement_prompt}</p>

      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1.5">
          File path in your repository
          <span className="ml-1 text-gray-400 font-normal">(leave blank if you don&apos;t have this)</span>
        </label>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={`e.g. docs/ethics/${entry.control_id.toLowerCase()}-evidence.pdf`}
          className="w-full px-3 py-2 text-sm font-mono border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent placeholder-gray-300 bg-gray-50"
        />
      </div>

      {value.trim() === "" && (
        <p className="text-xs text-gray-400">
          Leaving this blank means you don&apos;t have this artefact — it will be marked as <span className="font-medium text-red-500">missing</span>.
        </p>
      )}
    </div>
  );
}

export default function SupplementPageClient() {
  const params = useParams();
  const router = useRouter();
  const scanId = params.scanId as string;

  const [values, setValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: entries = [], isLoading, isError } = useQuery({
    queryKey: ["supplements", scanId],
    queryFn: () => apiClient.getSupplements(scanId),
    enabled: !!scanId,
  });

  // Pre-fill form with any previously declared paths once loaded
  useEffect(() => {
    if (entries.length === 0) return;
    setValues((prev) => {
      const next = { ...prev };
      for (const e of entries) {
        if (!(e.control_id in next)) {
          next[e.control_id] = e.declared_path ?? "";
        }
      }
      return next;
    });
  }, [entries]);

  const grouped = entries.reduce<Record<string, SupplementRead[]>>((acc, e) => {
    const p = getPillar(e.control_id);
    (acc[p] ??= []).push(e);
    return acc;
  }, {});

  const pendingCount = entries.filter(
    (e) => e.status_after_supplement === "not_evaluable"
  ).length;

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      await Promise.all(
        entries.map((entry) =>
          apiClient.submitSupplement(
            scanId,
            entry.control_id,
            values[entry.control_id]?.trim() || null
          )
        )
      );
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto py-20 text-center">
        <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-gray-500 text-sm">Loading supplement entries…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="max-w-2xl mx-auto py-20 text-center">
        <p className="text-red-600 font-medium text-sm">Failed to load supplement entries.</p>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="max-w-2xl mx-auto py-20 text-center">
        <p className="text-gray-500 text-sm">No supplement entries for this scan.</p>
        <button
          onClick={() => router.push(`/report/${scanId}`)}
          className="mt-4 text-sm text-blue-600 hover:underline"
        >
          ← Back to report
        </button>
      </div>
    );
  }

  if (submitted) {
    const declaredCount = entries.filter((e) => (values[e.control_id] ?? "").trim()).length;
    const missingCount = entries.length - declaredCount;

    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
          <svg className="w-7 h-7 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Supplement submitted</h2>
        <p className="text-sm text-gray-500 mb-1">
          <span className="font-semibold text-amber-600">{declaredCount} artefact{declaredCount !== 1 ? "s" : ""} declared</span>
          {missingCount > 0 && (
            <span className="ml-1">· <span className="text-red-500 font-semibold">{missingCount} marked missing</span></span>
          )}
        </p>
        <p className="text-xs text-gray-400 mb-8">
          The report has been updated with your responses.
        </p>
        <button
          onClick={() => router.push(`/report/${scanId}`)}
          className="px-6 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-800 transition-colors"
        >
          View updated report →
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.push(`/report/${scanId}`)}
          className="text-xs text-gray-400 hover:text-gray-600 mb-3 flex items-center gap-1 transition-colors"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back to report
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Supplement Declaration</h1>
        <p className="text-sm text-gray-500 mt-1">
          These controls cannot be assessed from code alone. Point to where the evidence lives in your repository.
        </p>
      </div>

      {/* Info banner */}
      <div className="mb-6 p-4 bg-purple-50 border border-purple-100 rounded-xl flex gap-3">
        <span className="text-purple-400 text-lg leading-none flex-shrink-0">📋</span>
        <div className="text-sm text-purple-700 space-y-1">
          <p><span className="font-semibold">Fill in the file path</span> for each artefact (relative to your repo root).</p>
          <p><span className="font-semibold">Leave blank</span> if you don&apos;t have it — it will be recorded as missing.</p>
          <p>You can resubmit at any time to update your answers.</p>
        </div>
      </div>

      {pendingCount > 0 && (
        <p className="text-xs text-gray-400 mb-5">
          {pendingCount} of {entries.length} still pending · {entries.length - pendingCount} previously submitted
        </p>
      )}

      {/* Grouped controls */}
      <div className="space-y-8">
        {Object.entries(grouped)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([pillar, pillarEntries]) => (
            <div key={pillar}>
              <div className="flex items-center gap-3 mb-3">
                <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest whitespace-nowrap">
                  {pillar}
                </h2>
                <span className="text-xs text-gray-300 font-medium">{pillarEntries.length}</span>
                <div className="flex-1 h-px bg-gray-100" />
              </div>
              <div className="space-y-3">
                {pillarEntries.map((entry) => (
                  <SupplementCard
                    key={entry.control_id}
                    entry={entry}
                    value={values[entry.control_id] ?? ""}
                    onChange={(val) =>
                      setValues((prev) => ({ ...prev, [entry.control_id]: val }))
                    }
                    submitted={false}
                  />
                ))}
              </div>
            </div>
          ))}
      </div>

      {/* Submit */}
      <div className="mt-8 pt-6 border-t border-gray-100">
        {error && (
          <p className="text-sm text-red-600 mb-4 p-3 bg-red-50 rounded-lg border border-red-100">{error}</p>
        )}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <p className="text-xs text-gray-400">
            {Object.values(values).filter((v) => v.trim()).length} of {entries.length} paths filled in
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => router.push(`/report/${scanId}`)}
              className="px-4 py-2.5 text-sm font-medium text-gray-600 border border-gray-200 rounded-xl hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-6 py-2.5 text-sm font-semibold text-white bg-purple-600 rounded-xl hover:bg-purple-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              {submitting ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Saving…
                </>
              ) : (
                "Save all responses"
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
