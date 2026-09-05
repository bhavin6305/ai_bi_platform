import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Send, Sparkles, User, Copy, Upload, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { AibiApi, getSessionId } from "@/lib/aibi-api";

export const Route = createFileRoute("/app/chat")({
  head: () => ({ meta: [{ title: "AI Chat — AIBI Platform" }] }),
  component: ChatPage,
});

type Msg = { id: string; role: "user" | "ai"; text: string; sql?: string; followups?: string[]; pending?: boolean };

const SUGGESTIONS = [
  "What are the top trends in this data?",
  "Show me the biggest anomalies",
  "Which segment is driving revenue?",
  "Summarize this dataset in 3 bullets",
];

function ChatPage() {
  const [sessionId, setSid] = useState<string | null>(null);
  useEffect(() => setSid(getSessionId()), []);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const historyQuery = useQuery({
    queryKey: ["chat-history", sessionId],
    queryFn: () => AibiApi.chatHistory(sessionId!),
    enabled: !!sessionId,
  });

  useEffect(() => {
    if (!historyQuery.data) return;
    setMessages(historyQuery.data.messages.flatMap((message) => [
      { id: `history-user-${message.insight_id}`, role: "user" as const, text: message.question },
      { id: `history-ai-${message.insight_id}`, role: "ai" as const, text: message.answer, sql: message.sql_used ?? undefined },
    ]));
  }, [historyQuery.data]);

  const mut = useMutation({
    mutationFn: (q: string) => AibiApi.chat(sessionId!, q),
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || !sessionId || mut.isPending) return;
    const uid = crypto.randomUUID();
    const aid = crypto.randomUUID();
    setMessages((m) => [...m, { id: uid, role: "user", text }, { id: aid, role: "ai", text: "", pending: true }]);
    setInput("");
    try {
      const res = await mut.mutateAsync(text);
      // simulated typing
      const full = res.answer ?? "";
      let i = 0;
      const iv = setInterval(() => {
        i += Math.max(2, Math.round(full.length / 60));
        setMessages((prev) => prev.map((m) => m.id === aid ? {
          ...m,
          text: full.slice(0, i),
          sql: res.sql_used,
          followups: i >= full.length ? (res.followup_questions ?? []) : undefined,
          pending: i < full.length,
        } : m));
        if (i >= full.length) clearInterval(iv);
      }, 25);
    } catch (e: any) {
      setMessages((prev) => prev.map((m) => m.id === aid ? { ...m, text: "Sorry — I couldn't reach the analysis service.", pending: false } : m));
      toast.error(e?.response?.data?.detail ?? "Chat request failed");
    }
  };

  if (!sessionId) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-24 text-center">
        <div className="mx-auto h-16 w-16 rounded-2xl grid place-items-center"
             style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 0 48px -8px rgba(124,58,237,0.6)" }}>
          <Upload className="h-7 w-7 text-white" />
        </div>
        <h1 className="mt-6 text-2xl font-semibold text-white">Upload data to start chatting</h1>
        <p className="mt-2 text-sm text-white/50">The AI needs a dataset to answer questions about.</p>
        <Link to="/app/upload" className="mt-6 inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium text-white"
              style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)" }}>
          Upload data <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6 py-10">
          {historyQuery.isLoading ? (
            <div className="py-20 text-center text-sm text-white/40">Loading conversation...</div>
          ) : messages.length === 0 ? (
            <div className="text-center py-12">
              <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
                className="mx-auto h-16 w-16 rounded-2xl grid place-items-center"
                style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 0 48px -8px rgba(124,58,237,0.6)" }}>
                
              </motion.div>
              <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                className="mt-6 text-3xl font-semibold tracking-tight"
                style={{ background: "linear-gradient(135deg,#c4b5fd,#93c5fd,#67e8f9)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                Ask anything about your data
              </motion.h1>
              <p className="mt-2 text-sm text-white/50">I'll write SQL, analyze the results, and explain what matters.</p>

              <div className="mt-8 grid sm:grid-cols-2 gap-2 max-w-xl mx-auto">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button key={s}
                    initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.05 }}
                    onClick={() => send(s)}
                    className="text-left rounded-xl px-4 py-3 text-sm text-white/70 hover:text-white transition"
                    style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    {s}
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((m) => m.role === "user" ? <UserBubble key={m.id} m={m} /> : <AIBubble key={m.id} m={m} onFollowup={send} />)}
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="px-6 py-4" style={{ borderTop: "1px solid rgba(255,255,255,0.06)", background: "rgba(8,8,16,0.85)", backdropFilter: "blur(20px)" }}>
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-2 rounded-2xl p-2"
               style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
              placeholder="Ask about your data…"
              className="flex-1 bg-transparent outline-none px-3 py-2.5 text-sm resize-none max-h-40 text-white placeholder:text-white/30"
            />
            <button
              aria-label="Send"
              disabled={!input.trim() || mut.isPending}
              onClick={() => send(input)}
              className="h-9 w-9 rounded-xl grid place-items-center text-white transition disabled:opacity-40"
              style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb)", boxShadow: "0 6px 20px -6px rgba(124,58,237,0.6)" }}>
              {mut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
          <div className="mt-2 text-center text-[11px] text-white/30">AIBI can make mistakes. Verify important decisions.</div>
        </div>
      </div>
    </div>
  );
}

function UserBubble({ m }: { m: Msg }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                className="flex gap-3 justify-end">
      <div className="max-w-[80%] rounded-2xl px-4 py-2.5 text-sm text-white"
           style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb)" }}>
        {m.text}
      </div>
      <div className="h-8 w-8 rounded-xl grid place-items-center shrink-0"
           style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
        <User className="h-4 w-4 text-white/60" />
      </div>
    </motion.div>
  );
}

function AIBubble({ m, onFollowup }: { m: Msg; onFollowup: (question: string) => void }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3">
      <div className="h-8 w-8 rounded-xl grid place-items-center shrink-0"
           style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 0 20px -6px rgba(124,58,237,0.6)" }}>
        <Sparkles className="h-4 w-4 text-white" />
      </div>
      <div className="flex-1 min-w-0 space-y-3">
        <div className="text-[15px] leading-relaxed whitespace-pre-wrap text-white/90">
          {m.text}
          {m.pending && <span className="ml-0.5 inline-block w-1.5 h-4 align-middle" style={{ background: "#a78bfa", animation: "pulse 1s infinite" }} />}
        </div>
        <AnimatePresence>
          {m.sql && !m.pending && (
            <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                        className="rounded-xl overflow-hidden"
                        style={{ background: "rgba(0,0,0,0.4)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <div className="flex items-center justify-between px-4 py-2" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <span className="text-[10px] uppercase tracking-widest text-white/40 font-semibold">SQL</span>
                <button aria-label="Copy SQL" onClick={() => { navigator.clipboard.writeText(m.sql ?? ""); toast.success("Copied"); }}
                        className="p-1.5 rounded text-white/40 hover:text-white hover:bg-white/5">
                  <Copy className="h-3.5 w-3.5" />
                </button>
              </div>
              <pre className="text-xs p-4 overflow-x-auto font-mono leading-relaxed" style={{ color: "#c4b5fd" }}>
                <code>{m.sql}</code>
              </pre>
            </motion.div>
          )}
        </AnimatePresence>
        {m.followups && m.followups.length > 0 && (
          <div className="pt-1">
            <div className="mb-2 text-[10px] uppercase tracking-widest text-white/35">Continue exploring</div>
            <div className="flex flex-wrap gap-2">
              {m.followups.slice(0, 3).map((followup) => (
                <button
                  key={followup}
                  type="button"
                  onClick={() => onFollowup(followup)}
                  className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-left text-xs text-white/65 transition hover:border-violet-400/40 hover:bg-violet-400/10 hover:text-white"
                >
                  {followup}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
