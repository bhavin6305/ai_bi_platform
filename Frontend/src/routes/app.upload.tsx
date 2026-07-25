import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import {
  Upload as UploadIcon, X, FileText, FileSpreadsheet, FileArchive,
  CheckCircle2, ArrowRight, AlertTriangle, Loader2, Sparkles, Link2
} from "lucide-react";
import {
  AibiApi, setSessionId, type UploadResponse, type ColumnSchema, type FileSummary
} from "@/lib/aibi-api";

export const Route = createFileRoute("/app/upload")({
  head: () => ({ meta: [{ title: "Upload Data — AIBI Platform" }] }),
  component: UploadPage,
});

const TYPE_STYLES: Record<string, { bg: string; fg: string; ring: string }> = {
  id:       { bg: "rgba(124,58,237,0.15)", fg: "#c4b5fd", ring: "rgba(124,58,237,0.35)" },
  datetime: { bg: "rgba(37,99,235,0.15)",  fg: "#93c5fd", ring: "rgba(37,99,235,0.35)" },
  currency: { bg: "rgba(16,185,129,0.15)", fg: "#6ee7b7", ring: "rgba(16,185,129,0.35)" },
  numeric:  { bg: "rgba(8,145,178,0.15)",  fg: "#67e8f9", ring: "rgba(8,145,178,0.35)" },
  category: { bg: "rgba(245,158,11,0.15)", fg: "#fcd34d", ring: "rgba(245,158,11,0.35)" },
  text:     { bg: "rgba(148,163,184,0.12)",fg: "#cbd5e1", ring: "rgba(148,163,184,0.25)" },
  boolean:  { bg: "rgba(236,72,153,0.15)", fg: "#f9a8d4", ring: "rgba(236,72,153,0.35)" },
};

const iconFor = (n: string) => {
  const ext = n.split(".").pop()?.toLowerCase();
  if (ext === "zip") return FileArchive;
  if (ext === "xlsx" || ext === "xls") return FileSpreadsheet;
  return FileText;
};

const PROGRESS_STEPS = [
  "Uploading files...",
  "Detecting schema...",
  "Running ETL pipeline...",
  "Inferring relationships...",
  "Calculating analytics...",
];

function UploadPage() {
  const nav = useNavigate();
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [stepIdx, setStepIdx] = useState(0);

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => [...prev, ...accepted]);
  }, []);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
      "application/vnd.ms-excel": [".xls"],
      "application/zip": [".zip"],
    },
  });

  const mut = useMutation({
    mutationFn: () => AibiApi.upload(files),
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setResult(data);
      toast.success(`Loaded ${data.schema_summary.files?.length ?? 0} tables · ${(data.schema_summary.total_rows ?? 0).toLocaleString()} rows`);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? err?.message ?? "Upload failed. Is the API running on port 8000?");
    },
  });

  useEffect(() => {
    if (!mut.isPending) { setStepIdx(0); return; }
    setStepIdx(0);
    const id = setInterval(() => setStepIdx((i) => (i + 1) % PROGRESS_STEPS.length), 1400);
    return () => clearInterval(id);
  }, [mut.isPending]);

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h1 className="text-3xl font-semibold tracking-tight text-white">Upload your dataset</h1>
        <p className="mt-2 text-sm text-white/50">Drop CSVs, Excel files, or a ZIP. We'll auto-detect the schema and build your workspace.</p>
      </motion.div>

      {/* Dropzone */}
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.05 }}
        className="mt-8">
        <div
          {...getRootProps()}
          className="relative rounded-2xl px-8 py-16 text-center cursor-pointer transition"
          style={{
            background: isDragActive ? "rgba(124,58,237,0.08)" : "rgba(13,13,24,0.6)",
            border: `2px dashed ${isDragActive ? "rgba(124,58,237,0.6)" : "rgba(255,255,255,0.12)"}`,
          }}>
          <input {...getInputProps()} />
          <div className="mx-auto h-14 w-14 rounded-2xl grid place-items-center"
               style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 0 40px -8px rgba(124,58,237,0.6)" }}>
            <UploadIcon className="h-6 w-6 text-white" />
          </div>
          <div className="mt-5 text-lg font-medium text-white">
            {isDragActive ? "Drop your files here" : "Drag & drop, or click to browse"}
          </div>
          <div className="mt-1.5 text-xs text-white/40">Supports .csv · .xlsx · .xls · .zip</div>
        </div>
      </motion.div>

      {/* File list */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.ul
            initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
            className="mt-4 space-y-2 overflow-hidden">
            {files.map((f, i) => {
              const Icon = iconFor(f.name);
              return (
                <motion.li key={f.name + i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-3 rounded-xl px-4 py-3"
                  style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
                  <div className="h-9 w-9 rounded-lg grid place-items-center" style={{ background: "rgba(124,58,237,0.15)" }}>
                    <Icon className="h-4 w-4" style={{ color: "#c4b5fd" }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-white truncate">{f.name}</div>
                    <div className="text-[11px] text-white/40 font-mono">{(f.size / 1024).toFixed(1)} KB</div>
                  </div>
                  <button aria-label={`Remove ${f.name}`}
                          onClick={(e) => { e.stopPropagation(); setFiles((p) => p.filter((_, idx) => idx !== i)); }}
                          className="p-2 rounded-md text-white/40 hover:text-white hover:bg-white/5">
                    <X className="h-4 w-4" />
                  </button>
                </motion.li>
              );
            })}
          </motion.ul>
        )}
      </AnimatePresence>

      {/* Run button */}
      <div className="mt-6">
        <button
          disabled={files.length === 0 || mut.isPending}
          onClick={() => mut.mutate()}
          className="w-full inline-flex items-center justify-center gap-2 rounded-xl px-6 py-4 text-sm font-semibold text-white transition disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 12px 40px -12px rgba(124,58,237,0.6)" }}>
          {mut.isPending ? (
            <><Loader2 className="h-4 w-4 animate-spin" /> <AnimatePresence mode="wait">
              <motion.span key={stepIdx} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.3 }}>
                {PROGRESS_STEPS[stepIdx]}
              </motion.span></AnimatePresence></>
          ) : (
            <> Run Auto-Detection & ETL Pipeline</>
          )}
        </button>
      </div>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
                      className="mt-10 space-y-6">
            <div className="flex items-center gap-3 rounded-2xl px-5 py-4"
                 style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.25)" }}>
              <CheckCircle2 className="h-5 w-5" style={{ color: "#34d399" }} />
              <div className="flex-1 text-sm text-white">
                Loaded <span className="font-semibold">{result.schema_summary.files?.length ?? result.schema_summary.tables_loaded ?? 0}</span> tables ·
                {" "}<span className="font-semibold">{(result.schema_summary.total_rows ?? result.schema_summary.files?.reduce((a, f) => a + (f.row_count || 0), 0) ?? 0).toLocaleString()}</span> rows
              </div>
              <div className="text-[11px] font-mono text-white/40">session {result.session_id.slice(0, 8)}</div>
            </div>

            {(result.schema_summary.files ?? []).map((f, i) => (
              <FileCard key={f.file_name + i} f={f} delay={i * 0.08} />
            ))}

            {result.schema_summary.relationships && result.schema_summary.relationships.length > 0 && (
              <div className="rounded-2xl p-6" style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Link2 className="h-4 w-4" style={{ color: "#67e8f9" }} /> Detected Relationships
                </div>
                <div className="mt-4 space-y-2">
                  {result.schema_summary.relationships.map((r, idx) => (
                    <div key={idx} className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-mono"
                         style={{ background: "rgba(255,255,255,0.03)" }}>
                      <span className="text-white/80">{r.from}</span>
                      <ArrowRight className="h-3 w-3 text-white/30" />
                      <span className="text-white/80">{r.to}</span>
                      <div className="flex-1" />
                      <span className="text-[10px] uppercase tracking-widest px-2 py-0.5 rounded"
                            style={{ background: "rgba(124,58,237,0.15)", color: "#c4b5fd" }}>{r.confidence}</span>
                      <span className="text-xs text-white/50">{r.match_percent}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-2">
              <button onClick={() => nav({ to: "/app/dashboard" })}
                      className="inline-flex items-center gap-2 rounded-xl px-6 py-3.5 text-sm font-semibold text-white"
                      style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 12px 40px -12px rgba(124,58,237,0.6)" }}>
                View Dashboard <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function QualityRing({ score }: { score: number }) {
  const s = Math.max(0, Math.min(100, score));
  const c = 2 * Math.PI * 22;
  const color = s >= 80 ? "#10b981" : s >= 60 ? "#f59e0b" : "#ef4444";
  return (
    <div className="relative h-16 w-16">
      <svg viewBox="0 0 52 52" className="h-16 w-16 -rotate-90">
        <circle cx="26" cy="26" r="22" stroke="rgba(255,255,255,0.08)" strokeWidth="4" fill="none" />
        <motion.circle
          cx="26" cy="26" r="22" stroke={color} strokeWidth="4" fill="none" strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c - (c * s) / 100 }}
          transition={{ duration: 1, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-xs font-semibold" style={{ color }}>{s}</div>
    </div>
  );
}

function FileCard({ f, delay }: { f: FileSummary; delay: number }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay }}
                className="rounded-2xl p-6"
                style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
      <div className="flex items-start gap-4">
        <div className="h-11 w-11 rounded-xl grid place-items-center" style={{ background: "rgba(124,58,237,0.15)" }}>
          <FileText className="h-5 w-5" style={{ color: "#c4b5fd" }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-base font-semibold text-white truncate">{f.file_name}</div>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/50 font-mono">
            <span>{f.row_count?.toLocaleString()} rows</span>
            <span>{f.column_count} columns</span>
          </div>
        </div>
        <QualityRing score={f.quality_score ?? 0} />
      </div>

      <div className="mt-5 overflow-x-auto rounded-xl" style={{ border: "1px solid rgba(255,255,255,0.06)" }}>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-widest text-white/40" style={{ background: "rgba(255,255,255,0.03)" }}>
              <th className="px-4 py-2.5 font-medium">Column</th>
              <th className="px-4 py-2.5 font-medium">Type</th>
              <th className="px-4 py-2.5 font-medium text-right">Nulls</th>
              <th className="px-4 py-2.5 font-medium text-right">Unique</th>
              <th className="px-4 py-2.5 font-medium">Sample</th>
            </tr>
          </thead>
          <tbody>
            {f.columns?.map((c: ColumnSchema, i) => {
              const st = TYPE_STYLES[c.detected_type as string] ?? TYPE_STYLES.text;
              return (
                <tr key={c.column_name + i} style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                  <td className="px-4 py-2.5 font-mono text-white/85">{c.column_name}</td>
                  <td className="px-4 py-2.5">
                    <span className="inline-flex text-[10px] uppercase tracking-widest px-2 py-0.5 rounded font-semibold"
                          style={{ background: st.bg, color: st.fg, border: `1px solid ${st.ring}` }}>
                      {c.detected_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-white/60">{(c.null_percent ?? 0).toFixed(1)}%</td>
                  <td className="px-4 py-2.5 text-right font-mono text-white/60">{(c.unique_count ?? 0).toLocaleString()}</td>
                  <td className="px-4 py-2.5 font-mono text-white/50 truncate max-w-[220px]">{String(c.sample_value ?? "")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {f.issues && f.issues.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {f.issues.map((issue, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full"
                  style={{ background: "rgba(245,158,11,0.1)", color: "#fcd34d", border: "1px solid rgba(245,158,11,0.25)" }}>
              <AlertTriangle className="h-3 w-3" /> {issue}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}
