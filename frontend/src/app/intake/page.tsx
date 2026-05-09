"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiClient, type ProjectCreate, type ScanRead } from "@/lib/api";

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

  // Step 1: create project
  const createProject = useMutation({
    mutationFn: (data: ProjectCreate) => apiClient.createProject(data),
  });

  // Step 2: start scan
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

  return (
    <div className="max-w-lg mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Project Intake</h1>
      <p className="text-gray-600 mb-8">
        Submit an AI system repository for an ethics review. The pipeline will scan
        your repository against the AIGAP control registry.
      </p>

      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
        {/* Project Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Project Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="My AI System"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
          />
        </div>

        {/* GitHub URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            GitHub Repository URL
          </label>
          <input
            type="url"
            value={form.github_url ?? ""}
            onChange={(e) => setForm({ ...form, github_url: e.target.value || undefined })}
            placeholder="https://github.com/org/repo"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
          />
        </div>

        {/* Assurance Level */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Assurance Level <span className="text-red-500">*</span>
          </label>
          <select
            value={form.assurance_level}
            onChange={(e) => setForm({ ...form, assurance_level: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
          >
            <option value="ug">UG — Undergraduate (Tier 1 only)</option>
            <option value="pg">PG — Postgraduate (Tier 1–2)</option>
            <option value="capstone">Capstone (All tiers · vulnerable / rights-affecting users)</option>
            <option value="industrial">Industrial (All tiers · regulated sector — highest scrutiny)</option>
          </select>
        </div>

        {/* Uses GenAI */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="uses_genai"
            checked={form.uses_genai}
            onChange={(e) => setForm({ ...form, uses_genai: e.target.checked })}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <label htmlFor="uses_genai" className="text-sm text-gray-700">
            <span className="font-medium">Uses Generative AI</span>
            <br />
            <span className="text-gray-500">
              Check if your system uses LLMs, image generation, or other generative models.
            </span>
          </label>
        </div>

        {/* Uses Reliability / Classical AI */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="uses_rel_ai"
            checked={form.uses_rel_ai}
            onChange={(e) => setForm({ ...form, uses_rel_ai: e.target.checked })}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <label htmlFor="uses_rel_ai" className="text-sm text-gray-700">
            <span className="font-medium">Uses Reliability / Classical AI</span>
            <br />
            <span className="text-gray-500">
              Check if your system uses traditional ML models (TensorFlow, PyTorch, scikit-learn, XGBoost, etc.) in safety-critical or decision-making roles.
            </span>
          </label>
        </div>

        {/* Vulnerable Users */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="vulnerable_users"
            checked={form.vulnerable_users}
            onChange={(e) => setForm({ ...form, vulnerable_users: e.target.checked })}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <label htmlFor="vulnerable_users" className="text-sm text-gray-700">
            <span className="font-medium">Vulnerable User Base</span>
            <br />
            <span className="text-gray-500">
              System is used by children, elderly, or otherwise vulnerable populations.
              Activates ACC-05 and raises minimum assurance level to <strong>Capstone</strong>.
            </span>
          </label>
        </div>

        {/* Rights-Affecting */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="rights_affecting"
            checked={form.rights_affecting}
            onChange={(e) => setForm({ ...form, rights_affecting: e.target.checked })}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <label htmlFor="rights_affecting" className="text-sm text-gray-700">
            <span className="font-medium">Rights-Affecting Decisions</span>
            <br />
            <span className="text-gray-500">
              System makes or supports decisions about loans, hiring, benefits, medical treatment, or legal outcomes.
              Raises minimum assurance level to <strong>Capstone</strong>.
            </span>
          </label>
        </div>

        {/* Regulated Sector */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="regulated_sector"
            checked={form.regulated_sector}
            onChange={(e) => setForm({ ...form, regulated_sector: e.target.checked })}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <label htmlFor="regulated_sector" className="text-sm text-gray-700">
            <span className="font-medium">Regulated Sector</span>
            <br />
            <span className="text-gray-500">
              Deployed in healthcare, finance, insurance, or legal.
              Raises minimum assurance level to <strong>Industrial</strong> (highest scrutiny).
            </span>
          </label>
        </div>

        {/* Cross-Border Transfer */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="cross_border_transfer"
            checked={form.cross_border_transfer}
            onChange={(e) => setForm({ ...form, cross_border_transfer: e.target.checked })}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <label htmlFor="cross_border_transfer" className="text-sm text-gray-700">
            <span className="font-medium">Cross-Border Data Transfer</span>
            <br />
            <span className="text-gray-500">
              Personal data leaves the country of origin. Activates control <strong>PRV-07</strong> (international transfer compliance).
            </span>
          </label>
        </div>

        {/* Jurisdiction */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Jurisdiction(s)
            <span className="ml-1 text-xs font-normal text-gray-500">— select all that apply</span>
          </label>
          <div className="grid grid-cols-2 gap-2">
            {[
              { code: "EU",  label: "🇪🇺 EU / EEA",         note: "EU AI Act" },
              { code: "UK",  label: "🇬🇧 United Kingdom",    note: "UK AI Framework" },
              { code: "US",  label: "🇺🇸 United States",     note: "NIST RMF" },
              { code: "CA",  label: "🇨🇦 Canada",            note: "AIDA / PIPEDA" },
              { code: "AU",  label: "🇦🇺 Australia",         note: "AI Ethics Framework" },
              { code: "SG",  label: "🇸🇬 Singapore",         note: "PDPA / AI Gov Framework" },
              { code: "IN",  label: "🇮🇳 India",             note: "DPDP Act" },
              { code: "LK",  label: "🇱🇰 Sri Lanka",         note: "PDP Act" },
              { code: "AE",  label: "🇦🇪 UAE",               note: "AI Strategy 2031" },
              { code: "CN",  label: "🇨🇳 China",             note: "AIGC Regulations" },
              { code: "JP",  label: "🇯🇵 Japan",             note: "AI Guidelines" },
              { code: "BR",  label: "🇧🇷 Brazil",            note: "LGPD / AI Bill" },
            ].map(({ code, label, note }) => {
              const selected = (form.jurisdiction ?? "").split(",").map(s => s.trim()).filter(Boolean);
              const isChecked = selected.includes(code);
              const toggle = () => {
                const next = isChecked
                  ? selected.filter(s => s !== code)
                  : [...selected, code];
                setForm({ ...form, jurisdiction: next.join(", ") || undefined });
              };
              return (
                <label key={code} className={`flex items-start gap-2 p-2 rounded-md border cursor-pointer text-sm transition-colors ${isChecked ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-gray-300"}`}>
                  <input type="checkbox" checked={isChecked} onChange={toggle} className="mt-0.5 h-4 w-4 text-blue-600 border-gray-300 rounded" />
                  <span>
                    <span className="font-medium text-gray-800">{label}</span>
                    <br />
                    <span className="text-xs text-gray-500">{note}</span>
                  </span>
                </label>
              );
            })}
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Selected: <span className="font-medium">{form.jurisdiction || "none"}</span>
          </p>
        </div>

        {/* User-Facing */}
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="user_facing"
            checked={form.user_facing}
            onChange={(e) => setForm({ ...form, user_facing: e.target.checked })}
            className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded"
          />
          <label htmlFor="user_facing" className="text-sm text-gray-700">
            <span className="font-medium">Public-Facing System</span>
            <br />
            <span className="text-gray-500">
              System is accessible to end users (not purely internal tooling).
              Activates <strong>ACC-02</strong> and <strong>ACC-04</strong> accessibility controls.
            </span>
          </label>
        </div>

        {/* Registry Version */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Registry Version <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            value={form.registry_version}
            onChange={(e) => setForm({ ...form, registry_version: e.target.value })}
            placeholder="v1"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
          />
          <p className="mt-1 text-xs text-gray-500">
            Must match the loaded registry version (currently: v2).
          </p>
        </div>

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
          className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? "Starting scan…" : "Start Ethics Review"}
        </button>
      </form>
    </div>
  );
}
