/**
 * Typed API client for the ethiksa-cer backend.
 *
 * All requests are sent to NEXT_PUBLIC_API_URL (defaults to http://localhost:8000).
 * When NEXT_PUBLIC_API_KEY is set every request includes the X-API-Key header so
 * it passes the backend ApiKeyMiddleware.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY;

// ---------------------------------------------------------------------------
// Request helper
// ---------------------------------------------------------------------------

function buildHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json", ...extra };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  return headers;
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...buildHeaders(),
      ...(init.headers as Record<string, string> | undefined),
    },
  });
  if (!res.ok) {
    let detail: string;
    try {
      const body = await res.json();
      detail = body?.detail ?? res.statusText;
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail);
  }
  // 204 No Content
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Request / response types
// ---------------------------------------------------------------------------

export interface ProjectCreate {
  name: string;
  github_url?: string;
  assurance_level: string;
  uses_genai: boolean;
  registry_version: string;
}

export interface ProjectRead {
  id: string;
  name: string;
  github_url: string | null;
  assurance_level: string;
  uses_genai: boolean;
  registry_version: string;
  created_at: string;
  updated_at: string;
}

export interface ScanRead {
  id: string;
  project_id: string;
  status: string;
  celery_task_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ControlResultRead {
  id: string;
  scan_id: string;
  control_id: string;
  outcome: "PASS" | "PARTIAL" | "MISSING";
  evidence: Record<string, unknown> | null;
  explanation: string | null;
  remediation: string | null;
  created_at: string;
}

export interface AuditLogRead {
  id: string;
  scan_id: string;
  stage: string;
  event: string;
  payload: Record<string, unknown> | null;
  recorded_at: string;
}

export interface ControlRead {
  id: string;
  control_id: string;
  title: string;
  pillar: string;
  tier: number;
  description: string | null;
  applies_to_genai: boolean;
  applies_to_reliability: boolean;
  auto: boolean;
  plugins: string[];
  pass_criteria: string;
  partial_criteria: string;
  missing_criteria: string;
}

export interface ControlWrite {
  title: string;
  pillar: string;
  tier: number;
  description?: string | null;
  applies_to_genai: boolean;
  applies_to_reliability: boolean;
  auto: boolean;
  plugins: string[];
  pass_criteria: string;
  partial_criteria: string;
  missing_criteria: string;
}

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------

export const apiClient = {
  // Projects
  createProject: (data: ProjectCreate): Promise<ProjectRead> =>
    apiFetch("/api/v1/projects/", { method: "POST", body: JSON.stringify(data) }),

  listProjects: (): Promise<ProjectRead[]> => apiFetch("/api/v1/projects/"),

  getProject: (projectId: string): Promise<ProjectRead> =>
    apiFetch(`/api/v1/projects/${projectId}`),

  deleteProject: (projectId: string): Promise<void> =>
    apiFetch(`/api/v1/projects/${projectId}`, { method: "DELETE" }),

  // Scans
  createScan: (projectId: string): Promise<ScanRead> =>
    apiFetch("/api/v1/scans/", { method: "POST", body: JSON.stringify({ project_id: projectId }) }),

  getScan: (scanId: string): Promise<ScanRead> => apiFetch(`/api/v1/scans/${scanId}`),

  listScans: (projectId?: string): Promise<ScanRead[]> =>
    apiFetch(`/api/v1/scans/${projectId ? `?project_id=${projectId}` : ""}`),

  // Reports
  getFindings: (scanId: string): Promise<ControlResultRead[]> =>
    apiFetch(`/api/v1/reports/${scanId}/findings`),

  getAuditLog: (scanId: string): Promise<AuditLogRead[]> =>
    apiFetch(`/api/v1/reports/${scanId}/audit`),

  // Controls
  listControls: (): Promise<ControlRead[]> => apiFetch("/api/v1/controls/"),

  createControl: (controlId: string, data: ControlWrite): Promise<ControlRead> =>
    apiFetch(`/api/v1/controls/${controlId}`, { method: "POST", body: JSON.stringify(data) }),

  updateControl: (controlId: string, data: ControlWrite): Promise<ControlRead> =>
    apiFetch(`/api/v1/controls/${controlId}`, { method: "PUT", body: JSON.stringify(data) }),

  deleteControl: (controlId: string): Promise<void> =>
    apiFetch(`/api/v1/controls/${controlId}`, { method: "DELETE" }),

  getRegistryInfo: (): Promise<{ file: string; version: string }> =>
    apiFetch("/api/v1/controls/registry-info"),
};
