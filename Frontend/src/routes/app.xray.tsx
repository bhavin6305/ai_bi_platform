import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CircleHelp,
  Database,
  Hash,
  KeyRound,
  Link2,
  Search,
  Shapes,
  Table2,
  Type,
} from "lucide-react";
import { AibiApi, getSessionId, type SchemaColumn, type SchemaTable } from "@/lib/aibi-api";

export const Route = createFileRoute("/app/xray")({
  head: () => ({ meta: [{ title: "Data X-Ray — AIBI Platform" }] }),
  component: DataXRay,
});

const TYPE_COLORS: Record<string, string> = {
  id: "#a78bfa",
  datetime: "#38bdf8",
  currency: "#34d399",
  numeric: "#22d3ee",
  category: "#fbbf24",
  text: "#cbd5e1",
  boolean: "#fb7185",
};

function DataXRay() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [selectedField, setSelectedField] = useState<{ tableName: string; column: SchemaColumn } | null>(null);
  const [search, setSearch] = useState("");
  const schemaQuery = useQuery({
    queryKey: ["schema-xray", sessionId],
    queryFn: () => AibiApi.schema(sessionId!),
    enabled: Boolean(sessionId),
  });

  useEffect(() => setSessionId(getSessionId()), []);

  const tables = schemaQuery.data?.tables ?? [];
  const filteredTables = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return tables;
    return tables
      .map((table) => ({
        ...table,
        columns: table.columns.filter((column) =>
          `${table.table_name} ${column.column_name} ${column.detected_type}`.toLowerCase().includes(needle),
        ),
      }))
      .filter((table) => table.columns.length > 0 || table.table_name.toLowerCase().includes(needle));
  }, [search, tables]);

  const allColumns = tables.flatMap((table) => table.columns);
  const totalRows = Math.max(0, ...tables.map((table) => table.quality?.total_rows ?? 0));
  const qualityScores = tables.map((table) => table.quality?.score).filter((score): score is number => typeof score === "number");
  const averageQuality = qualityScores.length
    ? Math.round(qualityScores.reduce((total, score) => total + score, 0) / qualityScores.length)
    : null;
  const selectedTable = tables.find((table) => table.table_name === selectedField?.tableName);

  if (!sessionId) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-24 text-center">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-cyan-400/10 text-cyan-200"><Database className="h-7 w-7" /></div>
        <h1 className="mt-6 text-2xl font-semibold text-white">No dataset to inspect</h1>
        <p className="mt-2 text-sm text-white/50">Upload a dataset first to see its structure, relationships, and quality signals.</p>
        <Link to="/app/upload" className="mt-6 inline-flex items-center gap-2 rounded-lg bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950">Upload data <ArrowRight className="h-4 w-4" /></Link>
      </div>
    );
  }

  if (schemaQuery.isLoading) {
    return <div className="mx-auto max-w-7xl px-6 py-10"><div className="h-9 w-64 animate-pulse rounded bg-white/10" /><div className="mt-8 grid gap-4 md:grid-cols-3">{[0, 1, 2].map((item) => <div key={item} className="h-28 animate-pulse rounded-xl bg-white/[0.04]" />)}</div><div className="mt-5 h-96 animate-pulse rounded-xl bg-white/[0.04]" /></div>;
  }

  if (schemaQuery.isError) {
    return <div className="mx-auto max-w-3xl px-6 py-20 text-center"><AlertTriangle className="mx-auto h-8 w-8 text-amber-300" /><h1 className="mt-4 text-xl font-semibold text-white">Could not inspect this dataset</h1><p className="mt-2 text-sm text-white/50">The schema profile is unavailable. Try selecting the dataset again from History.</p></div>;
  }

  return (
    <div className="relative mx-auto max-w-[1500px] px-5 py-8 sm:px-8 sm:py-10">
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-72 bg-[radial-gradient(ellipse_at_15%_0%,rgba(34,211,238,0.12),transparent_52%),radial-gradient(ellipse_at_85%_0%,rgba(16,185,129,0.09),transparent_45%)]" />
      <motion.header initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-200/70"><Activity className="h-3.5 w-3.5" /> Dataset observatory</div>
          <h1 className="mt-3 text-3xl font-semibold text-white">Data X-Ray</h1>
          <p className="mt-2 text-sm text-white/50">A live structural scan of session <span className="font-mono text-white/70">{sessionId.slice(0, 8)}</span></p>
        </div>
        <label className="flex w-full items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 sm:w-72">
          <Search className="h-4 w-4 text-white/35" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find a table or field" className="w-full bg-transparent text-sm text-white outline-none placeholder:text-white/35" />
        </label>
      </motion.header>

      <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryTile label="Tables scanned" value={tables.length.toLocaleString()} icon={<Database className="h-4 w-4" />} tint="#38bdf8" />
        <SummaryTile label="Fields mapped" value={allColumns.length.toLocaleString()} icon={<Shapes className="h-4 w-4" />} tint="#a78bfa" />
        <SummaryTile label="Rows profiled" value={totalRows.toLocaleString()} icon={<Table2 className="h-4 w-4" />} tint="#34d399" />
        <SummaryTile label="Avg. quality" value={averageQuality === null ? "Not reported" : `${averageQuality}%`} icon={<CheckCircle2 className="h-4 w-4" />} tint={averageQuality !== null && averageQuality < 70 ? "#fbbf24" : "#34d399"} />
      </div>

      <div className="mt-6 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-4">
          {filteredTables.map((table, index) => <TableMap key={table.table_name} table={table} index={index} selectedField={selectedField?.tableName === table.table_name ? selectedField.column.column_name : null} onSelect={(column) => setSelectedField({ tableName: table.table_name, column })} />)}
          {filteredTables.length === 0 && <div className="rounded-xl border border-white/10 bg-white/[0.025] px-5 py-12 text-center text-sm text-white/45">No matching table or field.</div>}
          <RelationshipMap relationships={schemaQuery.data?.relationships ?? []} />
        </div>
        <ColumnInspector column={selectedField?.column ?? null} table={selectedTable} />
      </div>
    </div>
  );
}

function SummaryTile({ label, value, icon, tint }: { label: string; value: string; icon: React.ReactNode; tint: string }) {
  return <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.035] p-4">
    <div className="absolute right-0 top-0 h-20 w-20 opacity-[0.08]" style={{ background: `radial-gradient(circle at top right, ${tint}, transparent 72%)` }} />
    <div className="relative flex items-center justify-between"><span className="text-xs text-white/45">{label}</span><span style={{ color: tint }}>{icon}</span></div>
    <div className="relative mt-3 text-2xl font-semibold text-white">{value}</div>
  </motion.div>;
}

function TableMap({ table, index, selectedField, onSelect }: { table: SchemaTable; index: number; selectedField: string | null; onSelect: (column: SchemaColumn) => void }) {
  const quality = table.quality;
  return <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(index * 0.06, 0.3) }} className="overflow-hidden rounded-xl border border-white/[0.09] bg-[#10131b]/90">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-3.5 sm:px-5">
      <div className="flex min-w-0 items-center gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-cyan-300/10 text-cyan-200"><Table2 className="h-4 w-4" /></span><div className="min-w-0"><h2 className="truncate text-sm font-semibold text-white">{table.table_name}</h2><p className="mt-0.5 text-[11px] text-white/40">{table.columns.length} fields · {(quality?.total_rows ?? 0).toLocaleString()} rows</p></div></div>
      {quality && <QualityPill score={quality.score} />}
    </div>
    <div className="grid gap-2 p-3 sm:grid-cols-2 lg:grid-cols-3">
      {table.columns.map((column) => <ColumnNode key={column.column_name} column={column} selected={selectedField === column.column_name} onClick={() => onSelect(column)} />)}
    </div>
    {quality && (quality.issues_found.length > 0 || quality.actions_taken.length > 0) && <div className="border-t border-white/[0.06] px-4 py-3 text-xs text-white/45 sm:px-5">
      <span className="text-amber-200/80">{quality.issues_found.length} quality signal{quality.issues_found.length === 1 ? "" : "s"}</span><span className="px-2 text-white/20">/</span>{quality.actions_taken.length} cleaning action{quality.actions_taken.length === 1 ? "" : "s"} recorded
    </div>}
  </motion.section>;
}

function ColumnNode({ column, selected, onClick }: { column: SchemaColumn; selected: boolean; onClick: () => void }) {
  const kind = column.detected_type.toLowerCase();
  const tint = TYPE_COLORS[kind] ?? "#cbd5e1";
  const Icon = kind === "id" ? KeyRound : kind.includes("date") ? CalendarDays : kind === "numeric" || kind === "currency" ? Hash : kind === "category" ? Shapes : kind === "text" ? Type : CircleHelp;
  return <button onClick={onClick} className={`group min-w-0 rounded-lg border px-3 py-3 text-left transition ${selected ? "border-cyan-200/40 bg-cyan-300/[0.09]" : "border-white/[0.07] bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.05]"}`}>
    <span className="flex items-center gap-2"><Icon className="h-3.5 w-3.5 shrink-0" style={{ color: tint }} /><span className="truncate text-xs font-medium text-white/85">{column.column_name}</span></span>
    <span className="mt-2 flex items-center justify-between gap-2"><span className="text-[10px] uppercase tracking-wider" style={{ color: tint }}>{column.detected_type}</span><span className="text-[10px] text-white/35">{column.unique_count.toLocaleString()} unique</span></span>
    <span className="mt-2 block h-1 overflow-hidden rounded-full bg-white/[0.07]"><span className="block h-full rounded-full" style={{ width: `${Math.min(100, Math.max(0, column.null_percent))}%`, background: column.null_percent > 20 ? "#fbbf24" : tint, opacity: 0.9 }} /></span>
    <span className="mt-1.5 block text-[10px] text-white/35">{column.null_percent.toFixed(1)}% missing</span>
  </button>;
}

function QualityPill({ score }: { score: number }) {
  const color = score >= 85 ? "#34d399" : score >= 65 ? "#fbbf24" : "#fb7185";
  return <span className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium" style={{ color, borderColor: `${color}35`, background: `${color}10` }}><Activity className="h-3 w-3" />{score}% quality</span>;
}

function ColumnInspector({ column, table }: { column: SchemaColumn | null; table?: SchemaTable }) {
  if (!column) return <aside className="sticky top-24 rounded-xl border border-white/[0.08] bg-white/[0.025] p-5"><div className="grid h-10 w-10 place-items-center rounded-lg bg-violet-300/10 text-violet-200"><ArrowDownRight className="h-5 w-5" /></div><h2 className="mt-4 text-sm font-semibold text-white">Field inspector</h2><p className="mt-2 text-xs leading-relaxed text-white/45">Select any field to inspect its detected type, completeness, uniqueness, and observed values.</p><div className="mt-5 border-t border-white/[0.07] pt-4"><p className="text-[10px] uppercase tracking-[0.16em] text-white/30">How to read this map</p><div className="mt-3 space-y-2">{Object.entries(TYPE_COLORS).map(([type, color]) => <div key={type} className="flex items-center gap-2 text-xs capitalize text-white/55"><span className="h-2 w-2 rounded-full" style={{ background: color }} />{type}</div>)}</div></div></aside>;
  const tint = TYPE_COLORS[column.detected_type.toLowerCase()] ?? "#cbd5e1";
  return <motion.aside key={`${table?.table_name}.${column.column_name}`} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} className="sticky top-24 rounded-xl border border-white/[0.09] bg-[#11151e] p-5">
    <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] uppercase tracking-[0.16em] text-white/35">Selected field</p><h2 className="mt-2 break-all text-lg font-semibold text-white">{column.column_name}</h2><p className="mt-1 break-all font-mono text-[10px] text-white/35">{table?.table_name}</p></div><span className="rounded-md px-2 py-1 text-[10px]" style={{ color: tint, background: `${tint}14` }}>{column.detected_type}</span></div>
    <div className="mt-5 grid grid-cols-2 gap-2"><InspectorMetric label="Unique values" value={column.unique_count.toLocaleString()} /><InspectorMetric label="Missing values" value={column.null_count.toLocaleString()} /></div>
    <div className="mt-4 rounded-lg border border-white/[0.07] bg-white/[0.025] p-3"><div className="flex items-center justify-between text-xs"><span className="text-white/50">Completeness</span><span className="font-medium text-white">{(100 - column.null_percent).toFixed(1)}%</span></div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(100, 100 - column.null_percent))}%`, background: tint }} /></div></div>
    <div className="mt-5"><h3 className="text-[10px] uppercase tracking-[0.16em] text-white/35">Observed examples</h3><div className="mt-2 flex flex-wrap gap-1.5">{column.sample_values.length ? column.sample_values.slice(0, 8).map((sample, index) => <span key={`${String(sample)}-${index}`} className="max-w-full truncate rounded-md border border-white/[0.07] bg-white/[0.03] px-2 py-1 text-[10px] text-white/65">{sample === null ? "null" : String(sample)}</span>) : <span className="text-xs text-white/35">No sample values saved</span>}</div></div>
    {table?.quality && <div className="mt-5 border-t border-white/[0.07] pt-4"><h3 className="text-[10px] uppercase tracking-[0.16em] text-white/35">Table quality</h3><div className="mt-2 flex items-center justify-between text-xs"><span className="text-white/50">Duplicate rows</span><span className="text-white/80">{table.quality.duplicate_rows.toLocaleString()}</span></div><div className="mt-2 flex items-center justify-between text-xs"><span className="text-white/50">Columns with nulls</span><span className="text-white/80">{table.quality.columns_with_nulls.toLocaleString()}</span></div></div>}
  </motion.aside>;
}

function InspectorMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-white/[0.06] bg-white/[0.025] p-3"><p className="text-[10px] text-white/40">{label}</p><p className="mt-1 text-sm font-semibold text-white">{value}</p></div>;
}

function RelationshipMap({ relationships }: { relationships: Array<{ from_table: string; from_column: string; to_table: string; to_column: string; confidence: string; match_percent: number }> }) {
  return <section className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4 sm:p-5">
    <div className="flex items-center gap-2"><Link2 className="h-4 w-4 text-emerald-200" /><h2 className="text-sm font-semibold text-white">Detected relationships</h2><span className="ml-auto text-xs text-white/35">{relationships.length}</span></div>
    {relationships.length ? <div className="mt-4 space-y-2">{relationships.map((relationship, index) => <div key={`${relationship.from_table}.${relationship.from_column}-${relationship.to_table}.${relationship.to_column}-${index}`} className="grid items-center gap-2 rounded-lg border border-white/[0.06] bg-black/10 p-3 sm:grid-cols-[1fr_auto_1fr_auto]">
      <div className="min-w-0"><p className="truncate text-xs text-white/80">{relationship.from_table}</p><p className="truncate font-mono text-[10px] text-white/35">{relationship.from_column}</p></div><ArrowRight className="hidden h-4 w-4 text-emerald-200/60 sm:block" /><div className="min-w-0"><p className="truncate text-xs text-white/80">{relationship.to_table}</p><p className="truncate font-mono text-[10px] text-white/35">{relationship.to_column}</p></div><span className="text-[10px] text-emerald-200/70">{relationship.match_percent.toFixed(1)}% match</span>
    </div>)}</div> : <p className="mt-3 text-xs text-white/40">No cross-table links were detected for this upload. Single-table datasets are mapped above.</p>}
  </section>;
}
