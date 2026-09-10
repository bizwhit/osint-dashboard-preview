export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
export const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE_URL || API_BASE.replace(/^http/, 'ws');

export type Tool = { id: string; name: string; category: string; input_types: string[]; description: string; default_enabled: boolean };
export type ToolRun = { id: string; tool: string; status: string; results_count: number; started_at?: string; completed_at?: string; error_message?: string };
export type SearchResult = { id: string; tool: string; target: string; site?: string; url?: string; confidence: string; extracted_data: Record<string, unknown>; created_at: string };
export type Case = { id: string; investigation_id: string; input_type: string; query: string; status: string; selected_tools: string[]; auto_pivot_enabled: boolean; parent_case_id?: string; discovered_via?: string; created_at: string; started_at?: string; completed_at?: string; results: SearchResult[] };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) }, cache: 'no-store' });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail || `Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  tools: (type?: string) => request<Tool[]>(`/api/tools${type ? `?input_type=${encodeURIComponent(type)}` : ''}`),
  createSearch: (body: Record<string, unknown>) => request<{ case_id: string; investigation_id: string; status: string }>('/api/search', { method: 'POST', body: JSON.stringify(body) }),
  case: (id: string) => request<Case>(`/api/case/${id}`),
  toolRuns: (id: string) => request<ToolRun[]>(`/api/case/${id}/tool-runs`),
  investigations: () => request<Array<{ id: string; name: string; status: string; created_at: string }>>('/api/investigations'),
  toolHealth: (password: string) => request<Array<Tool & { status: string; detail: string }>>('/api/tools/health', { headers: { 'X-Admin-Password': password } }),
  audit: (password: string) => request<Array<Record<string, unknown>>>('/api/audit', { headers: { 'X-Admin-Password': password } }),
};
