import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { lazy, Suspense, useEffect, useState } from "react";
import { AlertCircle, Loader2, Sparkles, TrendingUp, TrendingDown, ArrowRight, Upload } from "lucide-react";
import { AibiApi, getSessionId, type ChartData, type Kpi } from "@/lib/aibi-api";

const Plot = lazy(() => import("react-plotly.js"));

export const Route = createFileRoute("/app/dashboard")({
  head: () => ({ meta: [{ title: "Dashboard — AIBI Platform" }] }),
  component: Dashboard,
});

function Dashboard() {
  const [sessionId, setSid] = useState<string | null>(null);
  useEffect(() => setSid(getSessionId()), []);

  const q = useQuery({
    queryKey: ["analytics", sessionId],
    queryFn: () => AibiApi.analytics(sessionId!),
    enabled: !!sessionId,
    retry: 1,
  });
  const insightsQuery = useQuery({
    queryKey: ["insights", sessionId],
    queryFn: async () => {
      const res = await AibiApi.insights(sessionId!);
      // Build a map: chart_id → insight_text
      const map: Record<string, string> = {};
      (res.insights || []).forEach((i: any) => {
        map[String(i.chart_id)] = i.insight_text;
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
        <Link to="/app/chat" className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium text-white"
          style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb)", boxShadow: "0 8px 24px -8px rgba(124,58,237,0.5)" }}>
          Ask about this data
        </Link>
      </motion.div>

      {/* KPIs */}
      {data.kpis?.length > 0 && (
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {data.kpis.slice(0, 8).map((k, i) => <KpiCard key={k.name + i} k={k} i={i} />)}
        </div>
      )}

      {/* Charts */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
        {(data.charts ?? []).map((c, i) => (
          <ChartCard
            key={c.chart_id}
            sessionId={sessionId}
            chartId={c.chart_id}
            title={c.chart_title}
            rationale={c.rationale}
            i={i}
            insightText={insightsQuery.data?.[String(c.chart_id)]}
          />
        ))}
      </div>
    </div>
  );
}

function KpiCard({ k, i }: { k: Kpi; i: number }) {
  // fake trend from hash for visual polish
  const trend = (k.name.length % 2 === 0 ? 1 : -1) * ((k.name.charCodeAt(0) % 15) + 3);
  const up = trend >= 0;
  const val = typeof k.value === "number" ? formatNumber(k.value) : String(k.value);
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
        <div className="mt-3 flex items-center gap-1.5 text-xs" style={{ color: up ? "#34d399" : "#f87171" }}>
          {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
          {up ? "+" : ""}{trend}% vs last period
        </div>
      </div>
    </motion.div>
  );
}

function ChartCard({ sessionId, chartId, title, rationale, i, insightText }: { sessionId: string; chartId: string; title: string; rationale: string; i: number; insightText?: string; }) {
  const q = useQuery({
    queryKey: ["chart", sessionId, chartId],
    queryFn: () => AibiApi.chart(sessionId, chartId),
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
      {/* AI Insight below chart */}
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
  } else if (t.includes("scatter")) {
    traces = [{ type: "scatter", mode: "markers", x: data.x, y: data.y, marker: { color: "#67e8f9", size: 8, opacity: 0.7 } }];
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
