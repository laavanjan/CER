"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiClient, type ProjectCreate, type ScanRead } from "@/lib/api";

const JURISDICTIONS = [
  { code: "EU", label: "🇪🇺 EU / EEA",       note: "EU AI Act" },
  { code: "UK", label: "🇬🇧 United Kingdom",  note: "UK AI Framework" },
  { code: "US", label: "🇺🇸 United States",   note: "NIST RMF" },
  { code: "CA", label: "🇨🇦 Canada",          note: "AIDA / PIPEDA" },
  { code: "AU", label: "🇦🇺 Australia",       note: "AI Ethics Framework" },
  { code: "SG", label: "🇸🇬 Singapore",       note: "PDPA / AI Gov Framework" },
  { code: "IN", label: "🇮🇳 India",           note: "DPDP Act" },
  { code: "LK", label: "🇱🇰 Sri Lanka",       note: "PDP Act" },
  { code: "AE", label: "🇦🇪 UAE",             note: "AI Strategy 2031" },
  { code: "CN", label: "🇨🇳 China",           note: "AIGC Regulations" },
  { code: "JP", label: "🇯🇵 Japan",           note: "AI Guidelines" },
  { code: "BR", label: "🇧🇷 Brazil",          note: "LGPD / AI Bill" },
];

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-3 bg-gray-50 border-b border-gray-200">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{title}</h2>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function CheckCard({
  id,
  checked,
  onChange,
  title,
  description,
}: {
  id: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  title: string;
  description: string;
}) {
  return (
    <label
      htmlFor={id}
      className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
        checked ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
      }`}
    >
      <input
        type="checkbox"
        id={id}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded shrink-0"
      />
      <span>
        <span className="block text-sm font-medium text-gray-800">{title}</span>
        <span className="block text-xs text-gray-500 mt-0.5">{description}</span>
      </span>
    </label>
  );
}

export default function IntakePage() {
  const router = useRouter();
  const [form, setForm] = useState<ProjectCreate>({
    name: "",
    github_url: "",
    assurance_level: "ug",
    uses_genai: false,
    uses_rel_ai: false,
    vulnerable_users: false,
    rights_affecting: false,
    regulated_sector: false,
    cross_border_transfer: false,
    jurisdiction: "",
    user_facing: true,
    registry_version: "v2",
  });
  const [error, setError] = useState<string | null>(null);

  const createProject = useMutation({
    mutationFn: (data: ProjectCreate) => apiClient.createProject(data),
  });

  const startScan = useMutation({
    mutationFn: (projectId: string) => apiClient.createScan(projectId),
    onSuccess: (scan: ScanRead) => {
      router.push(`/scan/${scan.id}`);
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const project = await createProject.mutateAsync(form);
      await startScan.mutateAsync(project.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    }
  };

  const isLoading = createProject.isPending || startScan.isPending;

  const selectedJurisdictions = (form.jurisdiction ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const toggleJurisdiction = (code: string) => {
    const next = selectedJurisdictions.includes(code)
      ? selectedJurisdictions.filter((s) => s !== code)
      : [...selectedJurisdictions, code];
    setForm({ ...form, jurisdiction: next.join(", ") || undefined });
  };

  return (
    <div className="max-w-3xl mx-auto pb-10">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Project Intake</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Submit an AI system repository for an ethics review against the AIGAP control registry.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">

        {/* ── Section 1: Project Details ── */}
        <SectionCard title="Project Details">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Project Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="My AI System"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 text-sm"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                GitHub Repository URL
              </label>
              <input
                type="url"
                value={form.github_url ?? ""}
                onChange={(e) => setForm({ ...form, github_url: e.target.value || undefined })}
                placeholder="https://github.com/org/repo"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Assurance Level <span className="text-red-500">*</span>
              </label>
              <select
                value={form.assurance_level}
                onChange={(e) => setForm({ ...form, assurance_level: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 text-sm"
              >
                <option value="ug">UG — Undergraduate (Tier 1 only)</option>
                <option value="pg">PG — Postgraduate (Tier 1–2)</option>
                <option value="capstone">Capstone (All tiers · vulnerable / rights-affecting)</option>
                <option value="industrial">Industrial (All tiers · regulated — highest scrutiny)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Registry Version <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={form.registry_version}
                onChange={(e) => setForm({ ...form, registry_version: e.target.value })}
                placeholder="v2"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 text-sm"
              />
              <p className="mt-1 text-xs text-gray-400">Currently loaded: v2</p>
            </div>
          </div>
        </SectionCard>

        {/* ── Section 2: AI Technology ── */}
        <SectionCard title="AI Technology">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <CheckCard
              id="uses_genai"
              checked={form.uses_genai}
              onChange={(v) => setForm({ ...form, uses_genai: v })}
              title="Generative AI"
              description="Uses LLMs, image generation, or other generative models."
            />
            <CheckCard
              id="uses_rel_ai"
              checked={form.uses_rel_ai}
              onChange={(v) => setForm({ ...form, uses_rel_ai: v })}
              title="Reliability / Classical AI"
              description="Uses traditional ML (TensorFlow, scikit-learn, XGBoost, etc.) in safety-critical roles."
            />
          </div>
        </SectionCard>

        {/* ── Section 3: Risk Profile ── */}
        <SectionCard title="Risk Profile">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <CheckCard
              id="vulnerable_users"
              checked={form.vulnerable_users}
              onChange={(v) => setForm({ ...form, vulnerable_users: v })}
              title="Vulnerable User Base"
              description="Children, elderly, or otherwise vulnerable populations. Raises minimum to Capstone."
            />
            <CheckCard
              id="rights_affecting"
              checked={form.rights_affecting}
              onChange={(v) => setForm({ ...form, rights_affecting: v })}
              title="Rights-Affecting Decisions"
              description="Loans, hiring, benefits, medical, or legal outcomes. Raises minimum to Capstone."
            />
            <CheckCard
              id="regulated_sector"
              checked={form.regulated_sector}
              onChange={(v) => setForm({ ...form, regulated_sector: v })}
              title="Regulated Sector"
              description="Healthcare, finance, insurance, or legal. Raises minimum to Industrial."
            />
            <CheckCard
              id="user_facing"
              checked={form.user_facing}
              onChange={(v) => setForm({ ...form, user_facing: v })}
              title="Public-Facing System"
              description="Accessible to end users (not purely internal tooling). Activates ACC-02 and ACC-04."
            />
          </div>
        </SectionCard>

        {/* ── Section 4: Compliance ── */}
        <SectionCard title="Compliance">
          <div className="space-y-4">
            <CheckCard
              id="cross_border_transfer"
              checked={form.cross_border_transfer}
              onChange={(v) => setForm({ ...form, cross_border_transfer: v })}
              title="Cross-Border Data Transfer"
              description="Personal data leaves the country of origin. Activates PRV-07 (international transfer compliance)."
            />

            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Jurisdiction(s){" "}
                <span className="font-normal text-gray-400 text-xs">— select all that apply</span>
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {JURISDICTIONS.map(({ code, label, note }) => {
                  const isChecked = selectedJurisdictions.includes(code);
                  return (
                    <label
                      key={code}
                      className={`flex items-start gap-2 p-2 rounded-md border cursor-pointer text-sm transition-colors ${
                        isChecked
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleJurisdiction(code)}
                        className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded shrink-0"
                      />
                      <span>
                        <span className="block font-medium text-gray-800 text-xs">{label}</span>
                        <span className="block text-xs text-gray-400">{note}</span>
                      </span>
                    </label>
                  );
                })}
              </div>
              {selectedJurisdictions.length > 0 && (
                <p className="mt-2 text-xs text-gray-500">
                  Selected:{" "}
                  <span className="font-medium text-gray-700">
                    {selectedJurisdictions.join(", ")}
                  </span>
                </p>
              )}
            </div>
          </div>
        </SectionCard>

        {/* Error */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-3 px-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {isLoading ? "Starting scan…" : "Start Ethics Review"}
        </button>
      </form>
    </div>
  );
}
