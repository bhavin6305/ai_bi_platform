import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { lazy, Suspense, useEffect, useState } from "react";
import { AlertCircle, Check, ChevronDown, Download, Loader2, Sparkles, ArrowRight, Upload } from "lucide-react";
import { AibiApi, getSessionId, type ChartData, type DashboardFilters, type FilterField, type Kpi } from "@/lib/aibi-api";

const Plot = lazy(() => import("react-plotly.js"));

export const Route = createFileRoute("/app/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — AIBI Platform" }] }),
  component: Dashboard,
});

function Dashboard() {
  const [sessionId, setSid] = useState<string | null>(null);
  const [compactMode, setCompactMode] = useState(() => readSavedSetting("compact_mode", false));
  const [showInsights, setShowInsights] = useState(() => readSavedSetting("show_insights", true));
  const [draftFilters, setDraftFilters] = useState<DashboardFilters>({});
  const [appliedFilters, setAppliedFilters] = useState<DashboardFilters>({});
  const [reporting, setReporting] = useState(false);
  useEffect(() => setSid(getSessionId()), []);
  useEffect(() => {
    const handleSettingsUpdate = (event: Event) => {
      const settings = (event as CustomEvent<{ compact_mode?: boolean; show_insights?: boolean }>).detail;
      if (typeof settings.compact_mode === "boolean") setCompactMode(settings.compact_mode);
      if (typeof settings.show_insights === "boolean") setShowInsights(settings.show_insights);
    };
    window.addEventListener("aibi-settings-updated", handleSettingsUpdate);
    return () => window.removeEventListener("aibi-settings-updated", handleSettingsUpdate);
  }, []);

  const filterMetadataQuery = useQuery({
    queryKey: ["filter-metadata", sessionId],
    queryFn: () => AibiApi.filterMetadata(sessionId!),
    enabled: !!sessionId,
    staleTime: 5 * 60 * 1000,
  });
  useEffect(() => {
    const fields = filterMetadataQuery.data?.fields ?? [];
    const firstDate = fields.find((field) => field.type === "date");
    const firstCategory = fields.find((field) => field.type === "category");
    if (firstDate || firstCategory) {
      setDraftFilters((current) => ({
        ...current,
        date_column: current.date_column ?? firstDate?.column,
        category_column: current.category_column ?? firstCategory?.column,
      }));
    }
  }, [filterMetadataQuery.data]);

  const q = useQuery({
    queryKey: ["analytics", sessionId, appliedFilters],
    queryFn: () => AibiApi.analytics(sessionId!, appliedFilters),
    enabled: !!sessionId,
    retry: 1,
  });
  const comparisonQuery = useQuery({
    queryKey: ["analytics-comparison", sessionId, appliedFilters],
    queryFn: () => AibiApi.comparison(sessionId!, appliedFilters),
    enabled: !!sessionId && Boolean(
      appliedFilters.date_column &&
      appliedFilters.date_from &&
      appliedFilters.date_to
    ),
    retry: 1,
  });
  const insightsQuery = useQuery({
    queryKey: ["insights", sessionId],
    queryFn: async () => {
      const res = await AibiApi.insights(sessionId!);
      const map: Record<string, string> = {};
      res.insights.forEach((insight) => {
        if (insight.insight_text?.trim()) {
          map[String(insight.chart_id)] = insight.insight_text.trim();
        }
      });
      return map;
    },
    enabled: !!sessionId,
  });
  if (!sessionId) return <EmptyState />;

  if (q.isLoading) return <LoadingSkeleton />;

  if (q.isError) return (
    <div className="max-w-5xl mx-auto px-6 py-20">
      <div className="rounded-2xl p-8 flex items-center gap-4"
        style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.25)" }}>
        <AlertCircle className="h-6 w-6" style={{ color: "#f87171" }} />
        <div>
          <div className="text-white font-semibold">Couldn't load analytics</div>
          <div className="text-sm text-white/50 mt-1">Make sure your backend is running on port 8000.</div>
        </div>
      </div>
    </div>
  );

  const data = q.data!;
  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-white">Executive Dashboard</h1>
          <p className="mt-2 text-sm text-white/50">Auto-generated from your dataset · session <span className="font-mono">{sessionId.slice(0, 8)}</span></p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" title="Download PDF report" aria-label="Download PDF report" disabled={reporting} onClick={async () => {
            setReporting(true);
            try {
              const blob = await AibiApi.report(sessionId, appliedFilters);
              const url = URL.createObjectURL(blob);
              const anchor = document.createElement("a");
              anchor.href = url;
              anchor.download = `aibi-report-${sessionId.slice(0, 8)}.pdf`;
              anchor.click();
              URL.revokeObjectURL(url);
            } finally {
              setReporting(false);
            }
          }} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/80 hover:bg-white/10 disabled:opacity-50">
            <Download className="h-4 w-4" /> {reporting ? "Preparing..." : "PDF report"}
          </button>
          <Link to="/app/chat" className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-white" style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb)", boxShadow: "0 8px 24px -8px rgba(124,58,237,0.5)" }}>Ask about this data</Link>
        </div>
      </motion.div>

      {filterMetadataQuery.data?.fields.length ? (
        <FilterBar
          fields={filterMetadataQuery.data.fields}
          draft={draftFilters}
          onChange={setDraftFilters}
          onApply={() => setAppliedFilters({ ...draftFilters })}
          onClear={() => { setDraftFilters({}); setAppliedFilters({}); }}
          isApplying={q.isFetching}
        />
      ) : null}

      {data.kpis?.length > 0 && (
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.kpis.slice(0, 8).map((k, i) => (
            <KpiCard
              key={k.name + i}
              k={k}
              i={i}
              comparison={comparisonQuery.data?.comparisons[k.name]}
              comparisonRequested={Boolean(
                appliedFilters.date_column &&
                appliedFilters.date_from &&
                appliedFilters.date_to
              )}
            />
          ))}
        </div>
      )}

      <div className={`mt-8 grid grid-cols-1 lg:grid-cols-2 ${compactMode ? "gap-2" : "gap-4"}`}>
        {(data.charts ?? []).map((c, i) => (
          <ChartCard
            key={c.chart_id}
            sessionId={sessionId}
            chartId={c.chart_id}
            title={c.chart_title}
            rationale={c.rationale}
            filters={appliedFilters}
            i={i}
            insightText={showInsights && !hasActiveFilters(appliedFilters) ? insightsQuery.data?.[String(c.chart_id)] : undefined}
          />
        ))}
      </div>
    </div>
  );
}

function KpiCard({
  k,
  i,
  comparison,
  comparisonRequested,
}: {
  k: Kpi;
  i: number;
  comparison?: {
    percent_change: number | null;
    direction: "up" | "down" | "flat";
    comparison_available: boolean;
  };
  comparisonRequested: boolean;
}) {
  const val = typeof k.value === "number" ? formatNumber(k.value) : String(k.value);
  const comparisonText = comparison?.comparison_available
    ? comparison.percent_change === null
      ? "No comparable baseline"
      : `${comparison.direction === "up" ? "↑" : comparison.direction === "down" ? "↓" : "→"} ${Math.abs(comparison.percent_change).toFixed(1)}% vs previous period`
    : comparisonRequested
      ? "No comparison available"
      : "Select a date range to compare";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: i * 0.05 }}
      className="relative rounded-2xl p-5 overflow-hidden"
      style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
      <div className="pointer-events-none absolute inset-0 opacity-40"
        style={{ background: "radial-gradient(circle at 100% 0%, rgba(124,58,237,0.15), transparent 60%)" }} />
      <div className="relative">
        <div className="text-[11px] uppercase tracking-widest text-white/40">{k.name}</div>
        <div className="mt-2 flex items-baseline gap-1.5">
          <span className="text-3xl font-semibold text-white tracking-tight">{val}</span>
          {k.unit && <span className="text-sm text-white/40">{k.unit}</span>}
        </div>
        <div className="mt-3 text-xs text-white/35">{comparisonText}</div>
      </div>
    </motion.div>
  );
}

function ChartCard({ sessionId, chartId, title, rationale, filters, i, insightText }: { sessionId: string; chartId: string; title: string; rationale: string; filters: DashboardFilters; i: number; insightText?: string; }) {
  const q = useQuery({
    queryKey: ["chart", sessionId, chartId, filters],
    queryFn: () => AibiApi.chart(sessionId, chartId, filters),
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: i * 0.05 }}
      className="rounded-2xl p-5"
      style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
      <div>
        <div className="text-sm font-semibold text-white">{title}</div>
        {rationale && <div className="mt-1 text-xs text-white/45">{rationale}</div>}
      </div>
      <div className="mt-4 h-[280px]">
        {q.isLoading && <div className="h-full grid place-items-center text-white/40"><Loader2 className="h-5 w-5 animate-spin" /></div>}
        {q.isError && <div className="h-full grid place-items-center text-sm text-white/40">Chart unavailable</div>}
        {q.data && (
          <Suspense fallback={<div className="h-full" />}>
            <PlotlyChart data={q.data} />
          </Suspense>
        )}
      </div>
      {insightText && (
        <div className="mt-3 pt-3 border-t border-white/[0.06]">
          <div className="flex items-start gap-2">
            <Sparkles className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: "#a78bfa" }} />
            <p className="text-xs leading-relaxed" style={{ color: "rgba(255,255,255,0.55)" }}>
              {insightText}
            </p>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function FilterBar({ fields, draft, onChange, onApply, onClear, isApplying }: { fields: FilterField[]; draft: DashboardFilters; onChange: (filters: DashboardFilters) => void; onApply: () => void; onClear: () => void; isApplying: boolean }) {
  const dateFields = fields.filter((field) => field.type === "date");
  const categoryFields = fields.filter((field) => field.type === "category");
  const selectedCategory = categoryFields.find((field) => field.column === draft.category_column);
  return (
    <div className="mt-6 rounded-2xl p-4" style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
      <div className="flex flex-wrap items-end gap-3">
        {dateFields.length > 0 && <label className="min-w-[150px] flex-1 text-[11px] uppercase tracking-widest text-white/40">Date field
          <CinematicSelect
            value={draft.date_column}
            options={dateFields.map((field) => ({ value: field.column, label: field.column }))}
            onChange={(value) => onChange({ ...draft, date_column: value, date_from: undefined, date_to: undefined })}
          />
        </label>}
        <label className="min-w-[135px] flex-1 text-[11px] uppercase tracking-widest text-white/40">From
          <input type="date" value={draft.date_from ?? ""} min={dateFields.find((field) => field.column === draft.date_column)?.min ?? undefined} max={draft.date_to ?? undefined} onChange={(event) => onChange({ ...draft, date_from: event.target.value || undefined })} className="mt-1.5 w-full rounded-lg bg-white/10 px-3 py-2 text-sm normal-case tracking-normal text-white outline-none" />
        </label>
        <label className="min-w-[135px] flex-1 text-[11px] uppercase tracking-widest text-white/40">To
          <input type="date" value={draft.date_to ?? ""} min={draft.date_from ?? undefined} max={dateFields.find((field) => field.column === draft.date_column)?.max ?? undefined} onChange={(event) => onChange({ ...draft, date_to: event.target.value || undefined })} className="mt-1.5 w-full rounded-lg bg-white/10 px-3 py-2 text-sm normal-case tracking-normal text-white outline-none" />
        </label>
        {categoryFields.length > 0 && <label className="min-w-[150px] flex-1 text-[11px] uppercase tracking-widest text-white/40">Category field
          <CinematicSelect
            value={draft.category_column}
            options={categoryFields.map((field) => ({ value: field.column, label: field.column }))}
            onChange={(value) => onChange({ ...draft, category_column: value, category_value: undefined })}
          />
        </label>}
        <label className="min-w-[150px] flex-1 text-[11px] uppercase tracking-widest text-white/40">Category value
          <CinematicSelect
            value={draft.category_value}
            placeholder="All values"
            options={(selectedCategory?.values ?? []).map((value) => ({ value, label: value }))}
            onChange={(value) => onChange({ ...draft, category_value: value || undefined })}
          />
        </label>
        <button type="button" onClick={onApply} disabled={isApplying} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{isApplying ? "Applying..." : "Apply"}</button>
        <button type="button" onClick={onClear} className="rounded-lg px-3 py-2 text-sm text-white/55 hover:text-white">Clear</button>
      </div>
    </div>
  );
}

function CinematicSelect({ value, options, onChange, placeholder = "Select an option" }: { value?: string; options: Array<{ value: string; label: string }>; onChange: (value: string) => void; placeholder?: string }) {
  const [open, setOpen] = useState(false);
  const selected = options.find((option) => option.value === value);
  return (
    <div className="relative mt-1.5">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2.5 text-left text-sm normal-case tracking-normal text-white outline-none transition focus:ring-2 focus:ring-violet-400/50"
        style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.11), rgba(255,255,255,0.045))", border: "1px solid rgba(255,255,255,0.1)", boxShadow: open ? "0 0 26px -12px rgba(167,139,250,0.9)" : "inset 0 1px 0 rgba(255,255,255,0.04)" }}
      >
        <span className={selected ? "text-white" : "text-white/45"}>{selected?.label ?? placeholder}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-white/50 transition-transform duration-200 ${open ? "rotate-180 text-violet-300" : ""}`} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 4, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.16, ease: "easeOut" }}
            role="listbox"
            className="absolute left-0 right-0 z-50 max-h-56 overflow-y-auto rounded-xl p-1.5 shadow-2xl"
            style={{ background: "linear-gradient(180deg, rgba(32,31,49,0.98), rgba(16,16,28,0.98))", border: "1px solid rgba(255,255,255,0.13)", boxShadow: "0 20px 50px -18px rgba(0,0,0,0.9), 0 0 30px -18px rgba(167,139,250,0.7)", backdropFilter: "blur(20px)" }}
          >
            {placeholder === "All values" && <SelectOption label="All values" value="" selected={!value} onSelect={() => { onChange(""); setOpen(false); }} />}
            {options.map((option) => <SelectOption key={option.value} {...option} selected={option.value === value} onSelect={() => { onChange(option.value); setOpen(false); }} />)}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SelectOption({ value, label, selected, onSelect }: { value: string; label: string; selected: boolean; onSelect: () => void }) {
  return (
    <button type="button" role="option" aria-selected={selected} onClick={onSelect} className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm text-white/75 transition hover:bg-violet-400/15 hover:text-white">
      <span>{label}</span>
      {selected && <Check className="h-3.5 w-3.5 text-violet-300" />}
    </button>
  );
}

function PlotlyChart({ data }: { data: ChartData }) {
  const layout: any = {
    autosize: true,
    margin: { l: 40, r: 16, t: 8, b: 40 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, sans-serif", color: "#94a3b8", size: 11 },
    xaxis: { gridcolor: "rgba(255,255,255,0.05)", zerolinecolor: "rgba(255,255,255,0.05)" },
    yaxis: { gridcolor: "rgba(255,255,255,0.05)", zerolinecolor: "rgba(255,255,255,0.05)" },
    showlegend: false,
    colorway: ["#7c3aed", "#2563eb", "#0891b2", "#10b981", "#f59e0b", "#ec4899"],
  };

  const t = (data.chart_type || "").toLowerCase();
  let traces: any[] = [];
  if (t.includes("pie") || t.includes("donut")) {
    traces = [{ type: "pie", labels: data.labels ?? data.x, values: data.values ?? data.y, hole: t.includes("donut") ? 0.55 : 0, marker: { colors: ["#7c3aed", "#2563eb", "#0891b2", "#10b981", "#f59e0b", "#ec4899"] } }];
  } else if (t.includes("bar")) {
    traces = [{ type: "bar", x: data.x, y: data.y, marker: { color: "#7c3aed" } }];
  } else if (t.includes("heat")) {
    traces = [{ type: "heatmap", z: data.z, x: data.x, y: data.y, colorscale: [[0, "#0a0a12"], [1, "#7c3aed"]] }];
  } else if (t.includes("treemap")) {
    traces = [{ type: "treemap", labels: data.labels ?? data.x, values: data.values ?? data.y, parents: [""] }];
  } else if (t.includes("scatter")) {
    traces = [{ type: "scatter", mode: "markers", x: data.x, y: data.y, marker: { color: "#67e8f9", size: 8, opacity: 0.7 } }];
  } else if (t.includes("histogram")) {
    traces = [{ type: "histogram", x: data.x, marker: { color: "#0891b2" } }];
  } else if (t.includes("box")) {
    traces = [{ type: "box", y: data.y, name: data.name }];
  } else if (t.includes("funnel")) {
    traces = [{ type: "funnel", y: data.y, x: data.x, marker: { color: "#10b981" } }];
  } else {
    traces = [{
      type: "scatter", mode: "lines", x: data.x, y: data.y,
      line: { color: "#7c3aed", width: 2.5, shape: "spline" },
      fill: "tozeroy", fillcolor: "rgba(124,58,237,0.15)",
    }];
  }

  return (
    <Plot
      data={traces}
      layout={layout}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: "100%", height: "100%" }}
      useResizeHandler
    />
  );
}

function formatNumber(n: number) {
  const a = Math.abs(n);
  if (a >= 1e9) return (n / 1e9).toFixed(1) + "B";
  if (a >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (a >= 1e3) return (n / 1e3).toFixed(1) + "K";
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toFixed(2);
}

function readSavedSetting(key: string, fallback: boolean) {
  if (typeof window === "undefined") return fallback;
  try {
    const saved = JSON.parse(localStorage.getItem("aibi_settings") ?? "null");
    return typeof saved?.[key] === "boolean" ? saved[key] : fallback;
  } catch {
    return fallback;
  }
}

function hasActiveFilters(filters: DashboardFilters) {
  return Boolean(filters.date_from || filters.date_to || filters.category_value);
}

function LoadingSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-10">
      <div className="h-8 w-72 rounded-lg animate-pulse" style={{ background: "rgba(255,255,255,0.05)" }} />
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 rounded-2xl animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
        ))}
      </div>
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-[340px] rounded-2xl animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
        ))}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-24 text-center">
      <div className="mx-auto h-16 w-16 rounded-2xl grid place-items-center"
        style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 0 48px -8px rgba(124,58,237,0.6)" }}>
        <Upload className="h-7 w-7 text-white" />
      </div>
      <h1 className="mt-6 text-2xl font-semibold text-white">No dataset loaded yet</h1>
      <p className="mt-2 text-sm text-white/50">Upload data to auto-generate KPIs, charts, and insights.</p>
      <Link to="/app/upload" className="mt-6 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium text-white"
        style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)" }}>
        Upload data <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}
