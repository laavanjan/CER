"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiClient, type ProjectRead, type ScanRead } from "@/lib/api";

const STATUS_CONFIG: Record<string, { label: string; dot: string; badge: string }> = {
  COMPLETE:    { label: "Complete",  dot: "bg-emerald-500", badge: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  FAILED:      { label: "Failed",    dot: "bg-red-500",     badge: "bg-red-50 text-red-700 border-red-200" },
  PENDING:     { label: "Queued",    dot: "bg-gray-400",    badge: "bg-gray-50 text-gray-600 border-gray-200" },
};
function getStatusConfig(status: string) {
  return STATUS_CONFIG[status] ?? { label: status, dot: "bg-blue-500 animate-pulse", badge: "bg-blue-50 text-blue-700 border-blue-200" };
}

const LEVEL_LABELS: Record<string, string> = {
  ug: "UG", pg: "PG", capstone: "Capstone", industrial: "Industrial",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function ScanRow({ scan }: { scan: ScanRead }) {
  const router = useRouter();
  const cfg = getStatusConfig(scan.status);
  const isComplete = scan.status === "COMPLETE";
  const isRunning = !["COMPLETE", "FAILED", "PENDING"].includes(scan.status);

  return (
    <div className="flex items-center justify-between gap-4 py-3 px-4 rounded-lg hover:bg-gray-50 transition-colors group">
      <div className="flex items-center gap-3 min-w-0">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot} ${isRunning ? "animate-pulse" : ""}`} />
        <div className="min-w-0">
          <span className="text-xs font-mono text-gray-400 truncate block">{scan.id}</span>
          <span className="text-xs text-gray-400">{formatDate(scan.created_at)}</span>
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${cfg.badge}`}>
          {cfg.label}
        </span>
        {isComplete && (
          <button
            onClick={() => router.push(`/report/${scan.id}`)}
            className="text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline transition-colors"
          >
            View report →
          </button>
        )}
        {isRunning && (
          <button
            onClick={() => router.push(`/scan/${scan.id}`)}
            className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline transition-colors"
          >
            View progress →
          </button>
        )}
      </div>
    </div>
  );
}

function ProjectCard({
  project,
  scans,
}: {
  project: ProjectRead;
  scans: ScanRead[];
}) {
  const router = useRouter();
  const sorted = [...scans].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  const latestScan = sorted[0];
  const completeCount = scans.filter((s) => s.status === "COMPLETE").length;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
      {/* Project header */}
      <div className="px-5 py-4 border-b border-gray-100 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-base font-bold text-gray-900 truncate">{project.name}</h3>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-600 border border-indigo-100">
              {LEVEL_LABELS[project.assurance_level] ?? project.assurance_level}
            </span>
            {project.uses_genai && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-violet-50 text-violet-600 border border-violet-100">GenAI</span>
            )}
            {project.uses_rel_ai && (
              <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-blue-50 text-blue-600 border border-blue-100">Rel.AI</span>
            )}
          </div>
          {project.github_url && (
            <p className="text-xs text-gray-400 font-mono mt-1 truncate">{project.github_url}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs text-gray-400 whitespace-nowrap">
            {completeCount}/{scans.length} complete
          </span>
          <button
            onClick={() => router.push("/intake")}
            className="text-xs font-medium px-3 py-1.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Re-scan
          </button>
        </div>
      </div>

      {/* Scan list */}
      <div className="divide-y divide-gray-50">
        {sorted.length === 0 ? (
          <p className="px-5 py-4 text-xs text-gray-400">No scans yet.</p>
        ) : (
          sorted.map((scan) => <ScanRow key={scan.id} scan={scan} />)
        )}
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const router = useRouter();

  const { data: projects = [], isLoading: loadingProjects } = useQuery({
    queryKey: ["projects"],
    queryFn: () => apiClient.listProjects(),
  });

  const { data: allScans = [], isLoading: loadingScans } = useQuery({
    queryKey: ["allScans"],
    queryFn: () => apiClient.listAllScans(),
    refetchInterval: (query) => {
      const scans = query.state.data ?? [];
      const hasRunning = scans.some(
        (s) => !["COMPLETE", "FAILED", "PENDING"].includes(s.status)
      );
      return hasRunning ? 4000 : false;
    },
  });

  const isLoading = loadingProjects || loadingScans;
  const completeScans = allScans.filter((s) => s.status === "COMPLETE").length;
  const failedScans = allScans.filter((s) => s.status === "FAILED").length;
  const runningScans = allScans.filter(
    (s) => !["COMPLETE", "FAILED", "PENDING"].includes(s.status)
  ).length;

  // Group scans by project_id
  const scansByProject = allScans.reduce<Record<string, ScanRead[]>>((acc, s) => {
    const key = s.project_id;
    (acc[key] ??= []).push(s);
    return acc;
  }, {});

  // Sort projects by most recent scan
  const sortedProjects = [...projects].sort((a, b) => {
    const aLatest = scansByProject[a.id]?.[0]?.created_at ?? a.created_at;
    const bLatest = scansByProject[b.id]?.[0]?.created_at ?? b.created_at;
    return new Date(bLatest).getTime() - new Date(aLatest).getTime();
  });

  return (
    <div className="relative overflow-hidden">
      <div className="absolute -top-32 right-[-6rem] h-64 w-64 rounded-full bg-gradient-to-br from-teal-200/60 via-sky-200/40 to-amber-200/50 blur-3xl" />
      <div className="absolute top-24 -left-20 h-72 w-72 rounded-full bg-gradient-to-br from-amber-100/70 via-teal-100/50 to-transparent blur-3xl" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6">
        <section className="pt-10 pb-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <span className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-teal-700 bg-teal-50 border border-teal-100 rounded-full px-3 py-1">
                Ethics Review Command Center
              </span>
              <h1 className="mt-4 text-3xl sm:text-4xl font-semibold text-gray-900 leading-tight">
                Home base for auditable AI code reviews.
              </h1>
              <p className="mt-3 text-sm sm:text-base text-gray-600">
                Track every scan, surface gaps, and ship reviewer-ready evidence packs. This dashboard
                keeps your pipeline transparent from intake to audit.
              </p>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  onClick={() => router.push("/intake")}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-xl hover:bg-slate-800 transition-colors shadow-sm"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                  </svg>
                  Start new review
                </button>
                <button
                  onClick={() => router.push("/controls")}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-white text-slate-800 text-sm font-semibold rounded-xl border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition-colors"
                >
                  Browse controls
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
              <div className="rounded-2xl border border-slate-200 bg-white/80 backdrop-blur px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-gray-400">Projects</p>
                <p className="text-2xl font-semibold text-gray-900 mt-1">{projects.length}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white/80 backdrop-blur px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-gray-400">Total scans</p>
                <p className="text-2xl font-semibold text-gray-900 mt-1">{allScans.length}</p>
              </div>
              <div className="rounded-2xl border border-emerald-100 bg-emerald-50/60 px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-600">Completed</p>
                <p className="text-2xl font-semibold text-emerald-900 mt-1">{completeScans}</p>
              </div>
              <div className="rounded-2xl border border-amber-100 bg-amber-50/60 px-4 py-3">
                <p className="text-[10px] uppercase tracking-[0.2em] text-amber-600">In progress</p>
                <p className="text-2xl font-semibold text-amber-900 mt-1">{runningScans}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="pb-12">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Review History</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {projects.length} project{projects.length !== 1 ? "s" : ""} · {allScans.length} scan{allScans.length !== 1 ? "s" : ""} · {failedScans} failed
              </p>
            </div>
            <button
              onClick={() => router.push("/info")}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white text-sm font-semibold rounded-xl hover:bg-teal-700 transition-colors shadow-sm"
            >
              Learn more about ethics reviews
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20 text-gray-400">
              <svg className="animate-spin w-6 h-6 mr-3" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Loading history…
            </div>
          ) : sortedProjects.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-2xl border border-gray-200 border-dashed">
              <div className="w-12 h-12 rounded-xl bg-teal-50 flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
              </div>
              <h3 className="text-base font-semibold text-gray-700 mb-1">No reviews yet</h3>
              <p className="text-sm text-gray-400 mb-5">Submit a project to run your first ethics review.</p>
              <button
                onClick={() => router.push("/intake")}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-xl hover:bg-slate-800 transition-colors"
              >
                Start first review →
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {sortedProjects.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  scans={scansByProject[project.id] ?? []}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
