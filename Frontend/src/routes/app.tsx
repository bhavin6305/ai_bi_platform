import { createFileRoute, Link, Outlet, useRouterState } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  Upload, BarChart3, MessageSquareText, Settings, HelpCircle, Info,
  Search, Bell, Command,
} from "lucide-react";
import { Logo } from "@/components/aibi/atmosphere";

export const Route = createFileRoute("/app")({
  component: AppShell,
});

const nav: { to: string; label: string; icon: typeof Upload; live?: boolean }[] = [
  { to: "/app/upload", label: "Upload Data", icon: Upload },
  { to: "/app/dashboard", label: "Dashboard", icon: BarChart3, live: true },
  { to: "/app/chat", label: "AI Chat", icon: MessageSquareText },
  { to: "/info", label: "About", icon: Info },
];

function AppShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const active = nav.find((n) => pathname.startsWith(n.to))?.to ?? "/app/upload";
  const crumb = nav.find((n) => n.to === active)?.label ?? "App";

  return (
    <div className="min-h-screen flex" style={{ background: "#080810", color: "#f1f5f9" }}>
      {/* Sidebar */}
      <aside className="w-[220px] shrink-0 sticky top-0 h-screen flex flex-col"
             style={{ background: "rgba(10,10,18,0.95)", borderRight: "1px solid rgba(255,255,255,0.07)" }}>
        <Link to="/" className="px-5 py-5 block">
          <Logo />
        </Link>

        <nav className="px-3 mt-2 space-y-0.5">
          {nav.map((n) => {
            const isActive = pathname.startsWith(n.to);
            return (
              <Link
                key={n.to} to={n.to as any}
                className={`relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${isActive ? "text-white" : "text-white/55 hover:text-white hover:bg-white/5"}`}
              >
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active"
                    className="absolute inset-0 rounded-xl"
                    style={{ background: "linear-gradient(90deg, rgba(124,58,237,0.18), rgba(37,99,235,0.06))", border: "1px solid rgba(124,58,237,0.25)" }}
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <n.icon className="relative h-4 w-4 shrink-0" />
                <span className="relative flex-1">{n.label}</span>
                {n.live && (
                  <span className="relative text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded"
                        style={{ background: "rgba(16,185,129,0.15)", color: "#34d399", border: "1px solid rgba(16,185,129,0.25)" }}>
                    LIVE
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto px-3 pb-3 space-y-0.5">
          <button className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:text-white hover:bg-white/5 transition">
            <Settings className="h-4 w-4" /> Settings
          </button>
          <button className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:text-white hover:bg-white/5 transition">
            <HelpCircle className="h-4 w-4" /> Help
          </button>
          <div className="mt-3 flex items-center gap-2 rounded-lg px-3 py-2 text-[11px] text-white/50"
               style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping" style={{ background: "#10b981" }} />
              <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: "#10b981" }} />
            </span>
            API Connected · Port 8000
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="h-16 sticky top-0 z-20 flex items-center gap-4 px-6"
                style={{ background: "rgba(8,8,16,0.85)", borderBottom: "1px solid rgba(255,255,255,0.06)", backdropFilter: "blur(20px)" }}>
          <div className="text-sm flex items-center gap-2 text-white/45">
            <span>Platform</span>
            <span className="text-white/20">›</span>
            <span className="text-white">{crumb}</span>
          </div>
          <div className="flex-1" />
          <div className="hidden md:flex items-center gap-2 rounded-full px-3.5 py-2 text-xs text-white/50"
               style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <Search className="h-3.5 w-3.5" />
            <span>Search</span>
            <span className="flex items-center gap-1 ml-2 border border-white/10 rounded px-1.5 py-0.5 text-[10px]">
              <Command className="h-2.5 w-2.5" />K
            </span>
          </div>
          <button aria-label="Notifications" className="relative p-2 rounded-lg text-white/60 hover:text-white hover:bg-white/5">
            <Bell className="h-4 w-4" />
            <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full" style={{ background: "#a78bfa" }} />
          </button>
          <div className="h-8 w-8 rounded-full grid place-items-center text-xs font-semibold text-white"
               style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb)", boxShadow: "0 0 16px -4px rgba(124,58,237,0.6)" }}>B</div>
        </header>

        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
