"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient, type ControlRead, type ControlWrite } from "@/lib/api";
import { Pencil, Trash2, Plus, X, Check, Search, ChevronUp, ChevronDown } from "lucide-react";

// ---------------------------------------------------------------------------
// Pillar color palette
// ---------------------------------------------------------------------------

const PILLAR_STYLES: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  Governance:       { bg: "bg-violet-100",  text: "text-violet-800",  border: "border-violet-300",  dot: "bg-violet-500"  },
  Documentation:    { bg: "bg-blue-100",    text: "text-blue-800",    border: "border-blue-300",    dot: "bg-blue-500"    },
  Privacy:          { bg: "bg-teal-100",    text: "text-teal-800",    border: "border-teal-300",    dot: "bg-teal-500"    },
  Fairness:         { bg: "bg-pink-100",    text: "text-pink-800",    border: "border-pink-300",    dot: "bg-pink-500"    },
  Transparency:     { bg: "bg-amber-100",   text: "text-amber-800",   border: "border-amber-300",   dot: "bg-amber-500"   },
  Accountability:   { bg: "bg-red-100",     text: "text-red-800",     border: "border-red-300",     dot: "bg-red-500"     },
  Safety:           { bg: "bg-green-100",   text: "text-green-800",   border: "border-green-300",   dot: "bg-green-500"   },
  Security:         { bg: "bg-slate-100",   text: "text-slate-800",   border: "border-slate-300",   dot: "bg-slate-500"   },
  Explainability:   { bg: "bg-purple-100",  text: "text-purple-800",  border: "border-purple-300",  dot: "bg-purple-500"  },
  "Human Oversight":{ bg: "bg-yellow-100",  text: "text-yellow-800",  border: "border-yellow-300",  dot: "bg-yellow-500"  },
  Sustainability:   { bg: "bg-emerald-100", text: "text-emerald-800", border: "border-emerald-300", dot: "bg-emerald-500" },
};

const DEFAULT_PILLAR_STYLE = { bg: "bg-gray-100", text: "text-gray-700", border: "border-gray-300", dot: "bg-gray-400" };

function PillarBadge({ pillar }: { pillar: string }) {
  const s = PILLAR_STYLES[pillar] ?? DEFAULT_PILLAR_STYLE;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${s.bg} ${s.text} ${s.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {pillar}
    </span>
  );
}

const TIER_STYLES: Record<number, string> = {
  1: "bg-green-100 text-green-800 border-green-300",
  2: "bg-blue-100  text-blue-800  border-blue-300",
  3: "bg-orange-100 text-orange-800 border-orange-300",
};

function TierBadge({ tier }: { tier: number }) {
  const cls = TIER_STYLES[tier] ?? "bg-gray-100 text-gray-700 border-gray-300";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border ${cls}`}>
      T{tier}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Known pillars for the select dropdown
// ---------------------------------------------------------------------------

const PILLARS = [
  "Governance", "Documentation", "Privacy", "Fairness", "Transparency",
  "Accountability", "Safety", "Security", "Explainability", "Human Oversight", "Sustainability",
];

// ---------------------------------------------------------------------------
// Pillar → control-ID prefix mapping
// ---------------------------------------------------------------------------

const PILLAR_PREFIX_MAP: Record<string, string> = {
  Governance:        "GOV",
  Transparency:      "TRAN",
  Fairness:          "FAIR",
  Privacy:           "PRIV",
  Security:          "SEC",
  "Human Oversight": "HUMO",
  Safety:            "SAFE",
  Documentation:     "DOC",
  Accessibility:     "ACC",
  Risk:              "RISK",
  "Societal Impact": "SOC",
  // Pillars present in the registry not covered above
  Accountability:    "ACCT",
  Explainability:    "EXPL",
  Sustainability:    "SUST",
};

// ---------------------------------------------------------------------------
// Auto-ID generator
// ---------------------------------------------------------------------------

/**
 * Given a pillar name and the current list of controls, return the next
 * control ID for that pillar, e.g. "GOV-07".
 *
 * Rules:
 *  1. Look up the pillar's prefix in PILLAR_PREFIX_MAP.
 *  2. Find all existing control IDs that start with "<prefix>-".
 *  3. Parse the numeric suffix of each match.
 *  4. Return "<prefix>-<max+1>" zero-padded to 2 digits.
 *  5. If no matches exist, start at 01.
 */
function generateNextId(pillar: string, controls: ControlRead[]): string {
  const prefix = PILLAR_PREFIX_MAP[pillar];
  if (!prefix) return "";

  const prefixDash = `${prefix}-`;
  let max = 0;
  for (const c of controls) {
    if (c.id.startsWith(prefixDash)) {
      const suffix = c.id.slice(prefixDash.length);
      const n = parseInt(suffix, 10);
      if (!isNaN(n) && n > max) max = n;
    }
  }
  const next = (max + 1).toString().padStart(2, "0");
  return `${prefix}-${next}`;
}

// ---------------------------------------------------------------------------
// Empty form template
// ---------------------------------------------------------------------------

const EMPTY_FORM: ControlWrite = {
  pillar: "Governance",
  tier: 1,
  auto: false,
  plugins: [],
  pass_criteria: "",
  partial_criteria: "",
  missing_criteria: "",
};

// ---------------------------------------------------------------------------
// Edit / Create Modal
// ---------------------------------------------------------------------------

interface ModalProps {
  initialId?: string;
  initialData?: ControlWrite;
  mode: "create" | "edit";
  existingControls: ControlRead[];
  onSave: (id: string, data: ControlWrite) => void;
  onClose: () => void;
  isSaving: boolean;
}

function ControlModal({ initialId = "", initialData = EMPTY_FORM, mode, existingControls, onSave, onClose, isSaving }: ModalProps) {
  const [controlId, setControlId] = useState(initialId);
  const [form, setForm] = useState<ControlWrite>(initialData);
  const [pluginInput, setPluginInput] = useState(initialData.plugins.join(", "));

  // Auto-generate the control ID whenever the pillar changes in create mode.
  useEffect(() => {
    if (mode !== "create") return;
    const generated = generateNextId(form.pillar, existingControls);
    if (generated) setControlId(generated);
  }, [form.pillar, mode, existingControls]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const plugins = pluginInput.split(",").map((p) => p.trim()).filter(Boolean);
    onSave(controlId, { ...form, plugins });
  };

  const field = (
    label: string,
    key: keyof ControlWrite,
    placeholder?: string,
    multiline?: boolean
  ) => (
    <div>
      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
        {label}
      </label>
      {multiline ? (
        <textarea
          rows={2}
          required
          value={form[key] as string}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          placeholder={placeholder}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
        />
      ) : (
        <input
          type="text"
          required
          value={form[key] as string}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          placeholder={placeholder}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      )}
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-indigo-600 to-violet-600 rounded-t-2xl">
          <h2 className="text-lg font-bold text-white">
            {mode === "create" ? "➕ Add New Control" : `✏️ Edit Control — ${initialId}`}
          </h2>
          <button onClick={onClose} className="text-white/80 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Control ID */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Control ID <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              disabled={mode === "edit"}
              value={controlId}
              onChange={(e) => setControlId(e.target.value.toUpperCase())}
              placeholder="GOV-03"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          {/* Pillar + Tier + Auto row */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Pillar</label>
              <select
                value={form.pillar}
                onChange={(e) => setForm({ ...form, pillar: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                {PILLARS.map((p) => <option key={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Tier</label>
              <select
                value={form.tier}
                onChange={(e) => setForm({ ...form, tier: Number(e.target.value) })}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
              >
                {[1, 2, 3].map((t) => <option key={t} value={t}>Tier {t}</option>)}
              </select>
            </div>
            <div className="flex flex-col justify-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <div
                  onClick={() => setForm({ ...form, auto: !form.auto })}
                  className={`relative w-10 h-5 rounded-full transition-colors ${form.auto ? "bg-indigo-500" : "bg-gray-300"}`}
                >
                  <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${form.auto ? "translate-x-5" : "translate-x-0.5"}`} />
                </div>
                <span className="text-sm font-medium text-gray-700">Auto scan</span>
              </label>
            </div>
          </div>

          {/* Plugins */}
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Plugins <span className="text-gray-400">(comma-separated)</span>
            </label>
            <input
              type="text"
              value={pluginInput}
              onChange={(e) => setPluginInput(e.target.value)}
              placeholder="governance_scanner, docs_scanner"
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400 font-mono"
            />
          </div>

          {/* Criteria */}
          {field("Pass criteria", "pass_criteria", "When is this control fully met?", true)}
          {field("Partial criteria", "partial_criteria", "When is it partially met?", true)}
          {field("Missing criteria", "missing_criteria", "When is it not met at all?", true)}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 rounded-lg transition-colors"
            >
              <Check size={15} />
              {isSaving ? "Saving…" : "Save Control"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Delete confirmation dialog
// ---------------------------------------------------------------------------

function DeleteDialog({ controlId, onConfirm, onCancel, isDeleting }: {
  controlId: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
            <Trash2 size={18} className="text-red-600" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Delete control</h3>
            <p className="text-sm text-gray-500">This cannot be undone.</p>
          </div>
        </div>
        <p className="text-sm text-gray-700 mb-6">
          Are you sure you want to delete <span className="font-mono font-semibold text-red-700">{controlId}</span>?
        </p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition-colors"
          >
            {isDeleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type SortKey = "id" | "pillar" | "tier" | "auto";

export default function ControlsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [pillarFilter, setPillarFilter] = useState<string>("All");
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [sortAsc, setSortAsc] = useState(true);

  const [modalMode, setModalMode] = useState<"create" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<ControlRead | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const { data: registryInfo } = useQuery({
    queryKey: ["registry-info"],
    queryFn: () => apiClient.getRegistryInfo(),
    staleTime: Infinity, // registry metadata never changes at runtime
  });

  const registryFile    = registryInfo?.file    ?? "—";
  const registryVersion = registryInfo?.version ?? "—";

  const { data: controls = [], isLoading, isError } = useQuery({
    queryKey: ["controls"],
    queryFn: () => apiClient.listControls(),
  });

  const saveMutation = useMutation({
    mutationFn: ({ id, data, isNew }: { id: string; data: ControlWrite; isNew: boolean }) =>
      isNew ? apiClient.createControl(id, data) : apiClient.updateControl(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["controls"] });
      setModalMode(null);
      setEditTarget(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.deleteControl(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["controls"] });
      setDeleteTarget(null);
    },
  });

  // Sorting
  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((a) => !a);
    else { setSortKey(key); setSortAsc(true); }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k
      ? (sortAsc ? <ChevronUp size={13} className="text-indigo-500" /> : <ChevronDown size={13} className="text-indigo-500" />)
      : <ChevronUp size={13} className="text-gray-300" />;

  // Filter + sort
  const visible = controls
    .filter((c) => {
      const q = search.toLowerCase();
      const matchSearch =
        !q ||
        c.id.toLowerCase().includes(q) ||
        c.pillar.toLowerCase().includes(q) ||
        c.pass_criteria.toLowerCase().includes(q) ||
        c.plugins.some((p) => p.toLowerCase().includes(q));
      const matchPillar = pillarFilter === "All" || c.pillar === pillarFilter;
      return matchSearch && matchPillar;
    })
    .sort((a, b) => {
      let cmp = 0;
      if (sortKey === "id")     cmp = a.id.localeCompare(b.id);
      if (sortKey === "pillar") cmp = a.pillar.localeCompare(b.pillar);
      if (sortKey === "tier")   cmp = a.tier - b.tier;
      if (sortKey === "auto")   cmp = Number(b.auto) - Number(a.auto);
      return sortAsc ? cmp : -cmp;
    });

  const uniquePillars = Array.from(new Set(controls.map((c) => c.pillar))).sort();

  const openCreate = () => { setEditTarget(null); setModalMode("create"); };
  const openEdit = (c: ControlRead) => { setEditTarget(c); setModalMode("edit"); };

  return (
    <div className="space-y-5">
      {/* ── Registry banner card ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        {/* Header strip */}
        <div className="bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-700 px-8 py-6">
          <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-6">
            {/* Left — title block */}
            <div className="flex items-center gap-5">
              {/* Icon block */}
              <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-white/15 border border-white/25 flex items-center justify-center shadow-inner">
                <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
                </svg>
              </div>
              {/* Text */}
              <div>
                <p className="text-indigo-200/80 text-[11px] font-mono uppercase tracking-[0.18em] mb-1">
                  AIGAP · Tool 02 · CER
                </p>
                <h1 className="text-3xl font-black text-white tracking-tight leading-none">
                  Control Registry
                </h1>
                {/* Stat pills */}
                <div className="flex items-center gap-2 mt-2.5">
                  <span className="inline-flex items-center gap-1.5 bg-white/15 border border-white/20 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-300" />
                    {controls.length} controls
                  </span>
                  <span className="inline-flex items-center gap-1.5 bg-white/15 border border-white/20 text-white text-xs font-semibold px-2.5 py-1 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-violet-300" />
                    {uniquePillars.length} pillars
                  </span>
                  <span className="inline-flex items-center gap-1.5 bg-white/10 border border-white/15 text-indigo-200 text-[11px] font-mono px-2.5 py-1 rounded-full">
                    {registryFile}
                  </span>
                </div>
              </div>
            </div>

            {/* Right — Add Control button */}
            <button
              onClick={openCreate}
              className="inline-flex items-center gap-2 px-6 py-3 bg-white text-indigo-700 text-sm font-bold rounded-xl shadow-lg hover:shadow-xl hover:bg-indigo-50 active:scale-95 transition-all self-start sm:self-auto"
            >
              <Plus size={16} />
              Add Control
            </button>
          </div>
        </div>

        {/* ── Pillar tab bar ── */}
        <div className="border-b border-gray-100">
          <div className="flex overflow-x-auto scrollbar-none">
            {/* "All" tab */}
            <button
              onClick={() => setPillarFilter("All")}
              className={`flex-shrink-0 inline-flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                pillarFilter === "All"
                  ? "border-indigo-600 text-indigo-700 bg-indigo-50/60"
                  : "border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              All pillars
              <span className={`text-xs font-bold px-1.5 py-0.5 rounded-md ${
                pillarFilter === "All" ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-500"
              }`}>
                {controls.length}
              </span>
            </button>

            {/* Per-pillar tabs */}
            {uniquePillars.map((pillar) => {
              const s = PILLAR_STYLES[pillar] ?? DEFAULT_PILLAR_STYLE;
              const count = controls.filter((c) => c.pillar === pillar).length;
              const isActive = pillarFilter === pillar;
              return (
                <button
                  key={pillar}
                  onClick={() => setPillarFilter(isActive ? "All" : pillar)}
                  className={`flex-shrink-0 inline-flex items-center gap-2 px-5 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                    isActive
                      ? "border-indigo-600 text-indigo-700 bg-indigo-50/60"
                      : "border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300 hover:bg-gray-50"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.dot}`} />
                  {pillar}
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded-md ${
                    isActive ? "bg-indigo-100 text-indigo-700" : "bg-gray-100 text-gray-500"
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Search bar ── */}
      <div className="flex items-center gap-3">
        <div className="relative max-w-sm w-full">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by ID, pillar, or criteria…"
            className="w-full pl-9 pr-9 py-2 text-sm border border-gray-200 rounded-xl bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <X size={13} />
            </button>
          )}
        </div>
        {(search || pillarFilter !== "All") && (
          <span className="text-sm text-gray-500 whitespace-nowrap">
            {visible.length} result{visible.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20 text-gray-400">
          <svg className="animate-spin w-6 h-6 mr-3" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Loading controls…
        </div>
      ) : isError ? (
        <div className="py-12 text-center text-red-600 font-medium">Failed to load controls.</div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
          <div>
            <table className="w-full text-sm">
              <thead className="sticky top-14 z-20">
                <tr className="bg-gray-50 border-b-2 border-indigo-100 shadow-sm">
                  {([ ["id", "ID"], ["pillar", "Pillar"], ["tier", "Tier"], ["auto", "Auto"] ] as [SortKey, string][]).map(([k, label]) => (
                    <th
                      key={k}
                      onClick={() => toggleSort(k)}
                      className="bg-gray-50 px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-indigo-50 hover:text-indigo-700 transition-colors select-none whitespace-nowrap"
                    >
                      <span className="inline-flex items-center gap-1">
                        {label} <SortIcon k={k} />
                      </span>
                    </th>
                  ))}
                  <th className="bg-gray-50 px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap w-48">Plugins</th>
                  <th className="bg-gray-50 px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Pass Criteria</th>
                  <th className="bg-gray-50 px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right whitespace-nowrap">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-16 text-center">
                      <p className="text-gray-400 text-sm">No controls match your filter.</p>
                    </td>
                  </tr>
                ) : (
                  visible.map((c) => (
                    <tr
                      key={c.id}
                      className="hover:bg-indigo-50/30 transition-colors group"
                    >
                      {/* ID */}
                      <td className="px-4 py-3.5 font-mono font-bold text-indigo-700 whitespace-nowrap">
                        {c.id}
                      </td>
                      {/* Pillar */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <PillarBadge pillar={c.pillar} />
                      </td>
                      {/* Tier */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <TierBadge tier={c.tier} />
                      </td>
                      {/* Auto */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        {c.auto ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Yes
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-gray-500 bg-gray-50 border border-gray-200 px-2 py-0.5 rounded-full">
                            <span className="w-1.5 h-1.5 rounded-full bg-gray-400" /> Manual
                          </span>
                        )}
                      </td>
                      {/* Plugins */}
                      <td className="px-4 py-3.5">
                        <div className="flex flex-wrap gap-1">
                          {c.plugins.length > 0 ? c.plugins.map((p) => (
                            <span key={p} className="text-xs font-mono bg-slate-100 text-slate-600 border border-slate-200 px-1.5 py-0.5 rounded">
                              {p}
                            </span>
                          )) : (
                            <span className="text-xs text-gray-400 italic">—</span>
                          )}
                        </div>
                      </td>
                      {/* Pass criteria — takes all remaining space */}
                      <td className="px-4 py-3.5">
                        <p className="text-xs text-gray-700 leading-relaxed line-clamp-3">{c.pass_criteria}</p>
                      </td>
                      {/* Actions — fade in on row hover */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => openEdit(c)}
                            title="Edit"
                            className="p-1.5 text-indigo-500 hover:text-indigo-700 hover:bg-indigo-100 rounded-lg transition-colors"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => setDeleteTarget(c.id)}
                            title="Delete"
                            className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 text-xs text-gray-400 flex items-center justify-between">
            <span>
              Showing{" "}
              <span className="font-semibold text-gray-600">{visible.length}</span>
              {" "}of{" "}
              <span className="font-semibold text-gray-600">{controls.length}</span>
              {" "}controls
            </span>
            <span className="font-mono">{registryFile} · {registryVersion}</span>
          </div>
        </div>
      )}

      {/* Create / Edit modal */}
      {modalMode && (
        <ControlModal
          mode={modalMode}
          initialId={editTarget?.id ?? ""}
          initialData={editTarget ? {
            pillar: editTarget.pillar,
            tier: editTarget.tier,
            auto: editTarget.auto,
            plugins: editTarget.plugins,
            pass_criteria: editTarget.pass_criteria,
            partial_criteria: editTarget.partial_criteria,
            missing_criteria: editTarget.missing_criteria,
          } : EMPTY_FORM}
          existingControls={controls}
          onSave={(id, data) => saveMutation.mutate({ id, data, isNew: modalMode === "create" })}
          onClose={() => { setModalMode(null); setEditTarget(null); }}
          isSaving={saveMutation.isPending}
        />
      )}

      {/* Delete confirmation */}
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
