import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { AibiApi, setSessionId, type SessionListItem } from "@/lib/aibi-api";
import { useNavigate } from "@tanstack/react-router";
import { ArrowRight, Check, Clock, Database, Loader2, MessageSquareText, Pencil, X } from "lucide-react";

export const Route = createFileRoute("/app/sessions")({
  component: SessionsPage,
});

function SessionsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const q = useQuery({
    queryKey: ["sessions"],
    queryFn: () => AibiApi.sessions(),
  });
  const rename = useMutation({
    mutationFn: ({ sessionId, name }: { sessionId: string; name: string }) => AibiApi.renameSession(sessionId, name),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
      setEditingId(null);
      toast.success("Dataset name updated.");
    },
    onError: () => toast.error("Could not update this dataset name."),
  });

  const loadSession = (sessionId: string) => {
    setSessionId(sessionId);
    window.dispatchEvent(new Event("storage"));
    navigate({ to: "/app/dashboard" });
  };

  return (
    <div className="mx-auto max-w-5xl px-5 py-9 sm:px-8">
      <header className="flex items-end justify-between gap-4">
        <div><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-200/65">Workspace library</p><h1 className="mt-2 text-2xl font-semibold text-white">Dataset history</h1><p className="mt-1 text-sm text-white/45">Reopen an analysis or give it a name your team recognizes.</p></div>
        <span className="rounded-md border border-white/10 bg-white/[0.03] px-2.5 py-1.5 text-xs text-white/45">{q.data?.length ?? 0} datasets</span>
      </header>
      {q.isLoading && <div className="mt-8 flex items-center gap-2 text-sm text-white/45"><Loader2 className="h-4 w-4 animate-spin" />Loading datasets</div>}
      {q.isError && <p className="mt-8 rounded-lg border border-red-300/20 bg-red-300/5 p-4 text-sm text-red-200">Could not load dataset history.</p>}
      {!q.isLoading && !q.isError && q.data?.length === 0 && <div className="mt-8 rounded-xl border border-white/10 bg-white/[0.025] p-10 text-center"><Database className="mx-auto h-7 w-7 text-white/35" /><h2 className="mt-3 text-sm font-semibold text-white">No datasets yet</h2><p className="mt-1 text-xs text-white/40">Uploaded datasets will appear here.</p></div>}
      <div className="mt-5 space-y-2.5">
        {(q.data ?? []).map((session: SessionListItem) => (
          <div key={session.session_id} className="flex flex-wrap items-center gap-3 rounded-xl border border-white/[0.08] bg-[#10131b]/90 px-4 py-3.5 sm:px-5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-cyan-300/10 text-cyan-100"><Database className="h-4 w-4" /></span>
            <div className="min-w-0 flex-1">
              {editingId === session.session_id ? (
                <form className="flex max-w-lg gap-2" onSubmit={(event) => { event.preventDefault(); rename.mutate({ sessionId: session.session_id, name: draftName.trim() }); }}>
                  <input autoFocus value={draftName} onChange={(event) => setDraftName(event.target.value)} maxLength={120} className="min-w-0 flex-1 rounded-md border border-white/15 bg-white/[0.06] px-2.5 py-1.5 text-sm text-white outline-none focus:border-cyan-200/50" aria-label="Dataset name" />
                  <button disabled={!draftName.trim() || rename.isPending} title="Save name" aria-label="Save name" className="rounded-md bg-emerald-300/15 p-2 text-emerald-200 disabled:opacity-40"><Check className="h-4 w-4" /></button>
                  <button type="button" title="Cancel rename" aria-label="Cancel rename" onClick={() => setEditingId(null)} className="rounded-md p-2 text-white/45 hover:bg-white/10"><X className="h-4 w-4" /></button>
                </form>
              ) : <div className="flex min-w-0 items-center gap-2"><h2 className="truncate text-sm font-medium text-white">{session.name}</h2><button title="Rename dataset" aria-label={`Rename ${session.name}`} onClick={() => { setEditingId(session.session_id); setDraftName(session.name); }} className="rounded p-1 text-white/30 hover:bg-white/10 hover:text-white"><Pencil className="h-3.5 w-3.5" /></button></div>}
              <p className="mt-1 truncate font-mono text-[10px] text-white/30">{session.session_id}</p>
            </div>
            <div className="flex items-center gap-x-4 gap-y-1 text-[11px] text-white/40"><span>{session.file_count} file(s)</span><span>{session.total_rows.toLocaleString()} rows</span><span className="hidden items-center gap-1 sm:inline-flex"><Clock className="h-3 w-3" />{session.created_at?.slice(0, 10) ?? "Date unavailable"}</span></div>
            <div className="flex items-center gap-1">
              <button onClick={() => { setSessionId(session.session_id); navigate({ to: "/app/chat" }); }} title="Chat with this dataset" aria-label={`Chat with ${session.name}`} className="rounded-lg p-2 text-white/40 hover:bg-white/10 hover:text-white"><MessageSquareText className="h-4 w-4" /></button>
              <button onClick={() => loadSession(session.session_id)} title="Open dashboard" aria-label={`Open ${session.name}`} className="rounded-lg p-2 text-cyan-100/65 hover:bg-cyan-200/10 hover:text-cyan-100"><ArrowRight className="h-4 w-4" /></button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}