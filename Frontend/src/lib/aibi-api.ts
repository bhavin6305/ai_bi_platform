import axios from "axios";

export const API_BASE =
  (typeof window !== "undefined" && (window as any).__AIBI_API__) ||
  "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 300_000,
});

export type DetectedType =
  | "id" | "datetime" | "currency" | "numeric" | "category" | "text" | "boolean";

export interface ColumnSchema {
  column_name: string;
  detected_type: DetectedType | string;
  null_percent: number;
  unique_count: number;
  sample_value: unknown;
}

export interface FileSummary {
  file_name: string;
  row_count: number;
  column_count: number;
  quality_score: number;
  columns: ColumnSchema[];
  issues?: string[];
}

export interface Relationship {
  from: string;
  to: string;
  confidence: "high" | "medium" | "low";
  match_percent: number;
}

export interface UploadResponse {
  session_id: string;
  schema_summary: {
    files: FileSummary[];
    relationships?: Relationship[];
    total_rows?: number;
    tables_loaded?: number;
  };
}

export interface Kpi {
  name: string;
  value: number | string;
  unit?: string;
  category?: string;
}

export interface ChartMeta {
  chart_id: string;
  chart_type: string;
  chart_title: string;
  rationale: string;
}

export interface AnalyticsResponse {
  kpis: Kpi[];
  charts: ChartMeta[];
}

export interface ChartData {
  chart_type: string;
  title: string;
  rationale?: string;
  x?: (string | number)[];
  y?: (string | number)[];
  labels?: string[];
  values?: number[];
  z?: number[][];
}

export interface ChatResponse {
  answer: string;
  sql_used?: string;
}

export const AibiApi = {
  upload: async (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const { data } = await api.post("/api/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return normaliseUploadResponse(data);   // ← add this
  },

  analytics: async (sessionId: string) => {
    const { data } = await api.get(`/api/analytics/${sessionId}`);
    return normaliseAnalyticsResponse(data);  // ← add this
  },
  chart: async (sessionId: string, chartId: string) => {
    const { data } = await api.get<ChartData>(`/api/analytics/${sessionId}/chart/${chartId}`);
    return data;
  },
  chat: async (sessionId: string, question: string) => {
    const { data } = await api.post<ChatResponse>("/api/chat", { session_id: sessionId, question });
    return data;
  },
  status: async (sessionId: string) => {
    const { data } = await api.get<{ status: string }>(`/api/status/${sessionId}`);
    return data;
  },
};

export const getSessionId = () =>
  typeof window === "undefined" ? null : window.localStorage.getItem("session_id");

export const setSessionId = (id: string) => {
  if (typeof window !== "undefined") window.localStorage.setItem("session_id", id);
};

// Adapter — normalises FastAPI response shape to what the UI expects
export const normaliseUploadResponse = (raw: any): UploadResponse => {
  const summary = raw.schema_summary || {};
  const files: FileSummary[] = (summary.files || []).map((f: any) => ({
    file_name    : f.original_filename || f.file_name || "unknown",
    row_count    : f.row_count    || 0,
    column_count : f.column_count || 0,
    quality_score: f.quality?.score ?? f.quality_score ?? 0,
    columns      : (f.columns || []).map((c: any) => ({
      column_name  : c.column_name,
      detected_type: c.detected_type,
      null_percent : c.null_percent  || 0,
      unique_count : c.unique_count  || 0,
      sample_value : c.sample_values?.[0] ?? null,
    })),
    issues: f.quality?.issues_found || [],
  }));

  const relationships: Relationship[] = (summary.relationships || []).map((r: any) => ({
    from          : `${r.from_table}.${r.from_column}`,
    to            : `${r.to_table}.${r.to_column}`,
    confidence    : r.confidence,
    match_percent : r.match_percent,
  }));

  return {
    session_id    : raw.session_id,
    schema_summary: {
      files,
      relationships,
      total_rows   : raw.total_rows,
      tables_loaded: raw.tables_loaded,
    },
  };
};

// Normalise analytics response — API returns 'name' but UI expects 'name' ✓
// API returns 'chart_id' as number, UI expects string
export const normaliseAnalyticsResponse = (raw: any): AnalyticsResponse => ({
  kpis  : raw.kpis  || [],
  charts: (raw.charts || []).map((c: any) => ({
    ...c,
    chart_id: String(c.chart_id),
  })),
});