import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { motion } from "framer-motion";
import { Activity, AlertTriangle, BarChart3, Eye, LoaderCircle, Sparkles } from "lucide-react";
import { AibiApi, type ChartData } from "@/lib/aibi-api";

const Plot = lazy(() => import("react-plotly.js"));

export const Route = createFileRoute("/shared/$token")({
  component: SharedDashboard,
});

function SharedDashboard() {
  const { token } = Route.useParams();
  const query = useQuery({
    queryKey: ["shared-dashboard", token],
    queryFn: () => AibiApi.sharedDashboard(token),
  });

  if (query.isLoading)
    return (
      <main className="grid min-h-screen place-items-center bg-[#090e14] text-white/60">
        <div className="flex items-center gap-3 text-sm"><LoaderCircle className="h-4 w-4 animate-spin text-cyan-200" />Opening shared dashboard</div>
      </main>
    );
  if (query.isError)
    return (
      <main className="grid min-h-screen place-items-center bg-[#090e14] px-6 text-white">
        <section className="max-w-md text-center"><AlertTriangle className="mx-auto h-8 w-8 text-amber-300" /><h1 className="mt-5 text-2xl font-semibold">This link is unavailable</h1><p className="mt-2 text-sm leading-6 text-white/50">It may have expired or been removed. Ask the dashboard owner for a new link.</p></section>
      </main>
    );
  const data = query.data!;
  return (
    <main className="min-h-screen bg-[#090e14] text-[#f3f7f7]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[440px] bg-[radial-gradient(ellipse_at_12%_0%,rgba(25,153,151,0.13),transparent_54%),radial-gradient(ellipse_at_88%_0%,rgba(50,112,150,0.12),transparent_48%)]" />
      <div className="relative mx-auto max-w-[1440px] px-5 py-8 sm:px-8 sm:py-11">
        <motion.header initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-end justify-between gap-5 border-b border-white/[0.08] pb-6">
          <div><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-200/70"><Activity className="h-3.5 w-3.5" /> AIBI Nexus · Shared view</div><h1 className="mt-3 text-3xl font-semibold sm:text-4xl">{data.dashboard_name}</h1><p className="mt-2 text-sm text-white/45">Read-only analytics · Session {data.session_id.slice(0, 8)}</p></div>
          <span className="inline-flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-white/55"><Eye className="h-3.5 w-3.5 text-cyan-200" /> Public read-only link</span>
        </motion.header>

        <section aria-label="Key performance indicators" className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {data.kpis.map((kpi, index) => <motion.article key={`${kpi.name}-${index}`} initial={{ opacity: 0, y: 9 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.045 }} className="rounded-xl border border-white/[0.08] bg-[#111922]/85 p-4"><div className="text-[10px] font-medium uppercase tracking-[0.16em] text-white/42">{kpi.name}</div><div className="mt-2 text-2xl font-semibold text-white">{formatValue(kpi.value)}{kpi.unit && <span className="ml-1.5 text-sm font-normal text-white/40">{kpi.unit}</span>}</div></motion.article>)}
        </section>

        {data.insights.length > 0 && <section className="mt-6 rounded-xl border border-cyan-200/15 bg-cyan-200/[0.035] p-5"><div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.17em] text-cyan-100/70"><Sparkles className="h-3.5 w-3.5" /> Saved insights</div><div className="mt-4 grid gap-3 md:grid-cols-2">{data.insights.map((insight, index) => <p key={`${index}-${insight.slice(0, 32)}`} className="border-l border-cyan-200/40 pl-3 text-sm leading-6 text-white/70">{insight}</p>)}</div></section>}

        <section className="mt-8">
          <div className="flex items-center gap-2"><BarChart3 className="h-4 w-4 text-cyan-200" /><h2 className="text-sm font-semibold">Dashboard charts</h2><span className="text-xs text-white/35">{data.charts.length}</span></div>
          {data.charts.length ? <div className="mt-4 grid gap-4 xl:grid-cols-2">{data.charts.map((chart, index) => <motion.article key={chart.chart_id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.05, 0.3) }} className="min-w-0 rounded-xl border border-white/[0.08] bg-[#111922]/85 p-4 sm:p-5"><div><h3 className="text-sm font-semibold text-white">{chart.title}</h3>{chart.rationale && <p className="mt-1 text-xs text-white/42">{chart.rationale}</p>}</div><div className="mt-3 h-[290px]">{chart.data ? <Suspense fallback={<div className="grid h-full place-items-center text-xs text-white/40">Loading chart…</div>}><SharedPlot data={chart.data} /></Suspense> : <div className="grid h-full place-items-center text-xs text-white/40">Chart data unavailable</div>}</div></motion.article>)}</div> : <div className="mt-4 rounded-xl border border-white/[0.08] bg-white/[0.025] px-5 py-12 text-center"><BarChart3 className="mx-auto h-6 w-6 text-white/30" /><p className="mt-3 text-sm text-white/50">No saved charts are available for this dataset.</p></div>}
        </section>
        <footer className="mt-10 border-t border-white/[0.07] pt-4 text-[11px] text-white/30">Shared dashboard · Data is presented read-only · Session {data.session_id}</footer>
      </div>
    </main>
  );
}

function SharedPlot({ data }: { data: ChartData }) {
  const chartType = (data.chart_type || "line").toLowerCase();
  const palette = ["#5eead4", "#60a5fa", "#fbbf24", "#fb7185", "#a78bfa", "#4ade80"];
  let traces: any[];
  if (chartType.includes("pie") || chartType.includes("donut")) {
    traces = [{ type: "pie", labels: data.labels ?? data.x, values: data.values ?? data.y, hole: chartType.includes("donut") ? 0.52 : 0, marker: { colors: palette }, textfont: { color: "#f3f7f7" } }];
  } else if (chartType.includes("bar")) {
    traces = [{ type: "bar", x: data.x, y: data.y, marker: { color: "#5eead4", opacity: 0.86 } }];
  } else if (chartType.includes("heat")) {
    traces = [{ type: "heatmap", x: data.x, y: data.y, z: data.z, colorscale: [[0, "#17212a"], [0.5, "#167e84"], [1, "#a7f3d0"]], hoverongaps: false }];
  } else if (chartType.includes("treemap")) {
    traces = [{ type: "treemap", labels: data.labels ?? data.x, values: data.values ?? data.y, parents: data.parents ?? [""] }];
  } else if (chartType.includes("scatter")) {
    traces = [{ type: "scatter", mode: "markers", x: data.x, y: data.y, marker: { color: "#5eead4", size: 8, opacity: 0.78 } }];
  } else if (chartType.includes("histogram")) {
    traces = [{ type: "histogram", x: data.x, marker: { color: "#60a5fa" } }];
  } else if (chartType.includes("box")) {
    traces = [{ type: "box", y: data.y, name: data.name, marker: { color: "#5eead4" }, line: { color: "#5eead4" } }];
  } else if (chartType.includes("funnel")) {
    traces = [{ type: "funnel", y: data.y, x: data.x, marker: { color: "#5eead4" } }];
  } else {
    traces = [{ type: "scatter", mode: "lines+markers", x: data.x, y: data.y, line: { color: "#5eead4", width: 2.5, shape: "spline" }, marker: { size: 5 }, fill: "tozeroy", fillcolor: "rgba(94,234,212,0.08)" }];
  }
  return <Plot data={traces} layout={{ autosize: true, margin: { l: 48, r: 18, t: 12, b: 44 }, paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { family: "Plus Jakarta Sans, sans-serif", color: "#a6b4ba", size: 10 }, xaxis: { gridcolor: "rgba(255,255,255,0.06)", zerolinecolor: "rgba(255,255,255,0.08)" }, yaxis: { gridcolor: "rgba(255,255,255,0.06)", zerolinecolor: "rgba(255,255,255,0.08)" }, showlegend: false, colorway: palette }} config={{ displayModeBar: false, responsive: true }} style={{ width: "100%", height: "100%" }} useResizeHandler />;
}

function formatValue(value: number | string) {
  return typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value;
}
