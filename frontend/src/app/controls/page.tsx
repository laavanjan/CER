"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, type ControlRead, type ControlWrite } from "@/lib/api";
import { X, Check, Search } from "lucide-react";

// ---------------------------------------------------------------------------
// Pillar colours — keyed on exact DB names
// ---------------------------------------------------------------------------

const PILLAR_DOT: Record<string, string> = {
  "Governance & Accountability":               "bg-violet-500",
  "Data Governance & Privacy":                 "bg-teal-500",
  "Transparency & Explainability":             "bg-amber-500",
  "Safety & Robustness":                       "bg-green-500",
  "Fairness & Non-Discrimination":             "bg-pink-500",
  "Security, Misuse Prevention & Resilience":  "bg-slate-500",
  "Accessibility, Inclusion & Human Factors":  "bg-sky-500",
  "Human Oversight & Recourse":                "bg-yellow-500",
  "Documentation & Traceability":              "bg-blue-500",
  "Generative AI Overlay":                     "bg-purple-500",
  "Reliability AI Overlay":                    "bg-indigo-500",
};

const PILLAR_TEXT: Record<string, string> = {
  "Governance & Accountability":               "text-violet-600",
  "Data Governance & Privacy":                 "text-teal-600",
  "Transparency & Explainability":             "text-amber-600",
  "Safety & Robustness":                       "text-green-600",
  "Fairness & Non-Discrimination":             "text-pink-600",
  "Security, Misuse Prevention & Resilience":  "text-slate-600",
  "Accessibility, Inclusion & Human Factors":  "text-sky-600",
  "Human Oversight & Recourse":                "text-yellow-600",
  "Documentation & Traceability":              "text-blue-600",
  "Generative AI Overlay":                     "text-purple-600",
  "Reliability AI Overlay":                    "text-indigo-600",
};

const TIER_CONFIG = {
  1: { label: "T1", bg: "bg-green-50",  text: "text-green-700",  border: "border-green-200",  title: "Code-observable" },
  2: { label: "T2", bg: "bg-blue-50",   text: "text-blue-700",   border: "border-blue-200",   title: "Document-observable" },
  3: { label: "T3", bg: "bg-purple-50", text: "text-purple-700", border: "border-purple-200", title: "Design supplement" },
} as const;

// ---------------------------------------------------------------------------
// Pillars for the form dropdown
// ---------------------------------------------------------------------------

const PILLARS = [
  "Governance & Accountability",
  "Data Governance & Privacy",
  "Transparency & Explainability",
  "Safety & Robustness",
  "Fairness & Non-Discrimination",
  "Security, Misuse Prevention & Resilience",
  "Accessibility, Inclusion & Human Factors",
  "Human Oversight & Recourse",
  "Documentation & Traceability",
  "Generative AI Overlay",
  "Reliability AI Overlay",
];

// ---------------------------------------------------------------------------
// Edit / Create Modal (unchanged functionality, minimal look)
// ---------------------------------------------------------------------------

const EMPTY_FORM: ControlWrite = {
  title: "", pillar: PILLARS[0], tier: 1,
  applies_to_genai: false, applies_to_reliability: false,
  auto: false, plugins: [],
  pass_criteria: "", partial_criteria: "", missing_criteria: "",
};

function ControlModal({
  initialId = "", initialData = EMPTY_FORM, mode, existingControls, onSave, onClose, isSaving,
}: {
  initialId?: string; initialData?: ControlWrite; mode: "create" | "edit";
  existingControls: ControlRead[]; onSave: (id: string, data: ControlWrite) => void;
  onClose: () => void; isSaving: boolean;
}) {
  const [controlId, setControlId] = useState(initialId);
  const [form, setForm] = useState<ControlWrite>(initialData);
  const [pluginInput, setPluginInput] = useState(initialData.plugins.join(", "));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const plugins = pluginInput.split(",").map((p) => p.trim()).filter(Boolean);
    onSave(controlId, { ...form, plugins });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto border border-gray-100">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-sm font-bold text-gray-900">
            {mode === "create" ? "New control" : `Edit — ${initialId}`}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Control ID</label>
            <input
              type="text" required disabled={mode === "edit"} value={controlId}
              onChange={(e) => setControlId(e.target.value.toUpperCase())}
              placeholder="GOV-03"
              className="w-full px-3 py-2 text-sm font-mono border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Pillar</label>
              <select
                value={form.pillar} onChange={(e) => setForm({ ...form, pillar: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                {PILLARS.map((p) => <option key={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Tier</label>
              <select
                value={form.tier} onChange={(e) => setForm({ ...form, tier: Number(e.target.value) })}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                <option value={1}>T1 — Code-observable</option>
                <option value={2}>T2 — Document-observable</option>
                <option value={3}>T3 — Design supplement</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Plugins <span className="font-normal text-gray-400">(comma-separated)</span></label>
            <input
              type="text" value={pluginInput} onChange={(e) => setPluginInput(e.target.value)}
              placeholder="governance_scanner, docs_scanner"
              className="w-full px-3 py-2 text-sm font-mono border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          {(["pass_criteria", "partial_criteria", "missing_criteria"] as const).map((key) => (
            <div key={key}>
              <label className="block text-xs font-medium text-gray-500 mb-1 capitalize">
                {key.replace(/_/g, " ")}
              </label>
              <textarea
                rows={2} required value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
              />
            </div>
          ))}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              Cancel
            </button>
            <button
              type="submit" disabled={isSaving}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg transition-colors"
            >
              <Check size={14} />
              {isSaving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Delete dialog
// ---------------------------------------------------------------------------

function DeleteDialog({ controlId, onConfirm, onCancel, isDeleting }: {
  controlId: string; onConfirm: () => void; onCancel: () => void; isDeleting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6 border border-gray-100">
        <h3 className="font-bold text-gray-900 mb-1">Delete <span className="font-mono text-red-600">{controlId}</span>?</h3>
        <p className="text-sm text-gray-400 mb-5">This cannot be undone.</p>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">Cancel</button>
          <button onClick={onConfirm} disabled={isDeleting} className="px-4 py-2 text-sm font-semibold text-white bg-red-500 hover:bg-red-600 disabled:opacity-50 rounded-lg transition-colors">
            {isDeleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Control card
// ---------------------------------------------------------------------------

function ControlCard({ control, onEdit, onDelete }: {
  control: ControlRead;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const dot = PILLAR_DOT[control.pillar] ?? "bg-gray-400";
  const pillarText = PILLAR_TEXT[control.pillar] ?? "text-gray-500";
  const tier = TIER_CONFIG[control.tier as 1 | 2 | 3] ?? TIER_CONFIG[1];

  return (
    <div className="group bg-white border border-gray-100 rounded-xl p-4 hover:border-indigo-200 hover:shadow-sm transition-all flex flex-col gap-3">
      {/* Top row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dot}`} />
          <span className="font-mono text-sm font-bold text-gray-900">{control.id}</span>
          <span className={`text-xs font-bold px-1.5 py-0.5 rounded border ${tier.bg} ${tier.text} ${tier.border}`} title={tier.title}>
            {tier.label}
          </span>
        </div>
        {/* Actions — show on hover */}
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
          <button onClick={onEdit} className="p-1 text-gray-400 hover:text-indigo-600 transition-colors" title="Edit">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125" />
            </svg>
          </button>
          <button onClick={onDelete} className="p-1 text-gray-400 hover:text-red-500 transition-colors" title="Delete">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </button>
        </div>
      </div>

      {/* Pillar */}
      <p className={`text-xs font-medium ${pillarText} leading-none`}>{control.pillar}</p>

      {/* Pass criteria */}
      <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{control.pass_criteria}</p>

      {/* Plugins */}
      {control.plugins.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {control.plugins.map((p) => (
            <span key={p} className="text-[10px] font-mono bg-gray-50 text-gray-500 border border-gray-100 px-1.5 py-0.5 rounded">
              {p}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ControlsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [pillarFilter, setPillarFilter] = useState("All");
  const [tierFilter, setTierFilter] = useState(0);
  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<ControlRead | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const { data: registryInfo } = useQuery({
    queryKey: ["registry-info"],
    queryFn: () => apiClient.getRegistryInfo(),
    staleTime: Infinity,
  });

  const { data: controls = [], isLoading } = useQuery({
    queryKey: ["controls"],
    queryFn: () => apiClient.listControls(),
  });

  const saveMutation = useMutation({
    mutationFn: ({ id, data, isNew }: { id: string; data: ControlWrite; isNew: boolean }) =>
      isNew ? apiClient.createControl(id, data) : apiClient.updateControl(id, data),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["controls"] }); setModalMode(null); setEditTarget(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteControl(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["controls"] }); setDeleteTarget(null); },
  });

  const uniquePillars = Array.from(new Set(controls.map((c) => c.pillar))).sort();

  const tierCounts = { 1: 0, 2: 0, 3: 0 } as Record<number, number>;
  for (const c of controls) tierCounts[c.tier] = (tierCounts[c.tier] ?? 0) + 1;

  const visible = controls.filter((c) => {
    const q = search.toLowerCase();
    const matchSearch = !q || c.id.toLowerCase().includes(q) || c.pillar.toLowerCase().includes(q) || c.pass_criteria.toLowerCase().includes(q) || c.plugins.some((p) => p.toLowerCase().includes(q));
    const matchPillar = pillarFilter === "All" || c.pillar === pillarFilter;
    const matchTier = tierFilter === 0 || c.tier === tierFilter;
    return matchSearch && matchPillar && matchTier;
  }).sort((a, b) => a.id.localeCompare(b.id));

  return (
    <div className="flex gap-6 min-h-[calc(100vh-7rem)]">

      {/* ── Sidebar ── */}
      <aside className="w-56 flex-shrink-0 space-y-6">

        {/* Identity */}
        <div>
          {/* <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Registry</p> */}
          {/* <p className="text-xs font-mono text-gray-500">{registryInfo?.file ?? "—"}</p> */}
          <p className="text-[10px] text-gray-400 mt-0.5">Registry {controls.length} controls · {uniquePillars.length} pillars</p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            className="w-full pl-7 pr-7 py-1.5 text-xs border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <X size={11} />
            </button>
          )}
        </div>

        {/* Tier filter */}
        <div>
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Tier</p>
          <div className="space-y-1">
            <button
              onClick={() => setTierFilter(0)}
              className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${tierFilter === 0 ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100"}`}
            >
              All <span className="float-right text-gray-400 font-normal">{controls.length}</span>
            </button>
            {([1, 2, 3] as const).map((t) => {
              const cfg = TIER_CONFIG[t];
              return (
                <button
                  key={t}
                  onClick={() => setTierFilter(tierFilter === t ? 0 : t)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    tierFilter === t ? `${cfg.bg} ${cfg.text} font-semibold` : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  {cfg.label} <span className="text-[10px] font-normal text-gray-400 ml-1">{cfg.title}</span>
                  <span className="float-right text-gray-400 font-normal">{tierCounts[t] ?? 0}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Pillar filter */}
        <div>
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-2">Pillar</p>
          <div className="space-y-0.5">
            <button
              onClick={() => setPillarFilter("All")}
              className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${pillarFilter === "All" ? "bg-gray-900 text-white" : "text-gray-600 hover:bg-gray-100"}`}
            >
              All pillars
            </button>
            {uniquePillars.map((p) => {
              const dot = PILLAR_DOT[p] ?? "bg-gray-400";
              const count = controls.filter((c) => c.pillar === p).length;
              return (
                <button
                  key={p}
                  onClick={() => setPillarFilter(pillarFilter === p ? "All" : p)}
                  className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs transition-colors flex items-center gap-2 ${
                    pillarFilter === p ? "bg-indigo-50 text-indigo-700 font-semibold" : "text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`} />
                  <span className="truncate flex-1">{p}</span>
                  <span className="text-[10px] text-gray-400 flex-shrink-0">{count}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* New control */}
        <button
          onClick={() => { setEditTarget(null); setModalMode("create"); }}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add control
        </button>
      </aside>

      {/* ── Main grid ── */}
      <div className="flex-1 min-w-0">
        {/* Result count */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs text-gray-400">
            {visible.length === controls.length
              ? `${controls.length} controls`
              : `${visible.length} of ${controls.length} controls`}
            {(search || pillarFilter !== "All" || tierFilter !== 0) && (
              <button
                onClick={() => { setSearch(""); setPillarFilter("All"); setTierFilter(0); }}
                className="ml-2 text-indigo-500 hover:underline"
              >
                clear filters
              </button>
            )}
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-32 text-gray-300">
            <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
          </div>
        ) : visible.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 text-gray-400">
            <p className="text-sm">No controls match your filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {visible.map((c) => (
              <ControlCard
                key={c.id}
                control={c}
                onEdit={() => { setEditTarget(c); setModalMode("edit"); }}
                onDelete={() => setDeleteTarget(c.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Modals */}
      {modalMode && (
        <ControlModal
          mode={modalMode}
          initialId={editTarget?.id ?? ""}
          initialData={editTarget ? {
            title: editTarget.title, pillar: editTarget.pillar, tier: editTarget.tier,
            applies_to_genai: editTarget.applies_to_genai, applies_to_reliability: editTarget.applies_to_reliability,
            auto: editTarget.auto, plugins: editTarget.plugins,
            pass_criteria: editTarget.pass_criteria, partial_criteria: editTarget.partial_criteria,
            missing_criteria: editTarget.missing_criteria,
          } : EMPTY_FORM}
          existingControls={controls}
          onSave={(id, data) => saveMutation.mutate({ id, data, isNew: modalMode === "create" })}
          onClose={() => { setModalMode(null); setEditTarget(null); }}
          isSaving={saveMutation.isPending}
        />
      )}
      {deleteTarget && (
        <DeleteDialog
          controlId={deleteTarget}
          onConfirm={() => deleteMutation.mutate(deleteTarget)}
          onCancel={() => setDeleteTarget(null)}
          isDeleting={deleteMutation.isPending}
        />
      )}
    </div>
  );
}
