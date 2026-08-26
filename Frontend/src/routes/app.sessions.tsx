import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { AibiApi, setSessionId } from "@/lib/aibi-api";
import { useNavigate } from "@tanstack/react-router";
import { Clock, Database, ArrowRight, MessageSquareText } from "lucide-react";

export const Route = createFileRoute("/app/sessions")({
  component: SessionsPage,
});

function SessionsPage() {
  const navigate = useNavigate();
  const q = useQuery({
    queryKey: ["sessions"],
    queryFn : () => AibiApi.sessions(),
  });

  const loadSession = (sessionId: string) => {
    setSessionId(sessionId);
    window.dispatchEvent(new Event("storage"));
    navigate({ to: "/app/dashboard" });
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-4">
      <h1 className="text-2xl font-semibold text-white">Upload History</h1>
      {(q.data?.sessions ?? []).map((s: any) => (
        <div key={s.session_id}
          className="flex items-center gap-4 rounded-xl px-5 py-4 cursor-pointer"
          style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}
          onClick={() => loadSession(s.session_id)}
        >
          <Database className="h-5 w-5" style={{ color: "#a78bfa" }} />
          <div className="flex-1">
            <div className="text-sm font-mono text-white/60">{s.session_id.slice(0,8)}...</div>
            <div className="text-xs text-white/40 mt-0.5">
              {s.total_files} file(s) · {(s.total_rows || 0).toLocaleString()} rows
            </div>
          </div>
          <div className="text-xs text-white/30">{s.created_at?.slice(0, 10)}</div>
          <button
            aria-label={`Open chat for session ${s.session_id.slice(0, 8)}`}
            title="Open chat"
            onClick={(event) => { event.stopPropagation(); setSessionId(s.session_id); navigate({ to: "/app/chat" }); }}
            className="rounded-lg p-2 text-white/35 hover:bg-white/10 hover:text-white"
          >
            <MessageSquareText className="h-4 w-4" />
          </button>
          <ArrowRight className="h-4 w-4 text-white/30" />
        </div>
      ))}
    </div>
  );
}