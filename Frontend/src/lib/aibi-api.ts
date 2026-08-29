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

export interface KpiComparison {
  kpi_name: string;
  current_value: number;
  previous_value: number;
  absolute_change: number;
  percent_change: number | null;
  direction: "up" | "down" | "flat";
  comparison_available: boolean;
}

export interface KpiComparisonResponse {
  session_id: string;
  comparison_available: boolean;
  comparisons: Record<string, KpiComparison>;
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

export interface DashboardFilters {
  date_column?: string;
  date_from?: string;
  date_to?: string;
  category_column?: string;
  category_value?: string;
}

export interface FilterField {
  table: string;
  column: string;
  type: "date" | "category";
  min?: string | null;
  max?: string | null;
  values?: string[];
}

export interface FilterMetadataResponse {
  session_id: string;
  fields: FilterField[];
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
  name?: string;
}

export interface InsightsResponse {
  session_id: string;
  insights: Array<{
    chart_id: number | string;
    insight_text: string;
    generated_at?: string | null;
  }>;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: { id: number; full_name: string; email: string };
}

export interface UserSettings {
  full_name: string;
  email_updates: boolean;
  compact_mode: boolean;
  show_insights: boolean;
  timezone: string;
}

export interface NotificationItem {
  id: number;
  event_type: string;
  title: string;
  message: string;
  created_at: string | null;
  read: boolean;
}

export interface ChatResponse {
  session_id?: string;
  question?: string;
  answer: string;
  sql_used?: string;
  row_count?: number;
  followup_questions?: string[];
}

export interface ChatHistoryMessage {
  insight_id: number;
  question: string;
  answer: string;
  sql_used?: string | null;
  generated_at?: string | null;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ChatHistoryMessage[];
}

export const AibiApi = {
  upload: async (files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    const { data } = await api.post("/api/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return normaliseUploadResponse(data);
  },

  analytics: async (sessionId: string, filters: DashboardFilters = {}) => {
    const { data } = await api.get(`/api/analytics/${sessionId}`, { params: filters });
    return normaliseAnalyticsResponse(data);
  },
  comparison: async (sessionId: string, filters: DashboardFilters = {}) => {
    const { data } = await api.get<KpiComparisonResponse>(`/api/analytics/${sessionId}/comparison`, { params: filters });
    return data;
  },
  chart: async (sessionId: string, chartId: string, filters: DashboardFilters = {}) => {
    const { data } = await api.get<ChartData>(`/api/analytics/${sessionId}/chart/${chartId}`, { params: filters });
    return data;
  },
  filterMetadata: async (sessionId: string) => {
    const { data } = await api.get<FilterMetadataResponse>(`/api/analytics/${sessionId}/filters`);
    return data;
  },
  report: async (sessionId: string, filters: DashboardFilters = {}) => {
    const response = await api.get(`/api/reports/${sessionId}.pdf`, {
      params: filters,
      responseType: "blob",
    });
    return response.data as Blob;
  },
  chat: async (sessionId: string, question: string) => {
    const { data } = await api.post<ChatResponse>("/api/chat", { session_id: sessionId, question });
    return data;
  },
  chatHistory: async (sessionId: string) => {
    const { data } = await api.get<ChatHistoryResponse>(`/api/chat/${sessionId}/history`);
    return data;
  },
  status: async (sessionId: string) => {
    const { data } = await api.get<{ status: string }>(`/api/status/${sessionId}`);
    return data;
  },
  insights: async (sessionId: string) => {
    const { data } = await api.get<InsightsResponse>(`/api/analytics/${sessionId}/insights`);
    return data;
  },
  signup: async (fullName: string, email: string, password: string) => {
    const { data } = await api.post<AuthResponse>("/api/auth/signup", {
      full_name: fullName,
      email,
      password,
    });
    return data;
  },
  signin: async (email: string, password: string) => {
    const { data } = await api.post<AuthResponse>("/api/auth/signin", { email, password });
    return data;
  },
  logout: async () => {
    await api.post("/api/auth/logout", undefined, { headers: authHeaders() });
  },
  settings: async () => {
    const { data } = await api.get<{ settings: UserSettings }>("/api/auth/settings", { headers: authHeaders() });
    return data.settings;
  },
  updateSettings: async (settings: Partial<UserSettings>) => {
    const { data } = await api.patch<{ settings: UserSettings }>("/api/auth/settings", settings, { headers: authHeaders() });
    return data.settings;
  },
  notifications: async (sessionId: string) => {
    const { data } = await api.get<{ notifications: NotificationItem[] }>(`/api/notifications/${sessionId}`);
    return data.notifications;
  },
  markNotificationsRead: async (sessionId: string) => {
    await api.post(`/api/notifications/${sessionId}/read`);
  },
  sessions: async () => {
    const { data } = await api.get("/api/sessions");
    return data;
  },
};

export const getSessionId = () =>
  typeof window === "undefined" ? null : window.localStorage.getItem("session_id");

export const setSessionId = (id: string) => {
  if (typeof window !== "undefined") window.localStorage.setItem("session_id", id);
};

export const setAuthToken = (token: string) => {
  if (typeof window !== "undefined") window.localStorage.setItem("aibi_auth_token", token);
};

export const clearAuth = () => {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("aibi_auth_token");
    window.localStorage.removeItem("session_id");
  }
};

const authHeaders = () => {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("aibi_auth_token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
};

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

export const normaliseAnalyticsResponse = (raw: any): AnalyticsResponse => ({
  kpis  : raw.kpis  || [],
  charts: (raw.charts || []).map((c: any) => ({
    ...c,
    chart_id: String(c.chart_id),
  })),
});