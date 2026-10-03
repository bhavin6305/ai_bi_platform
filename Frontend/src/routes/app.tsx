import { createFileRoute, Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import {
  Upload,
  BarChart3,
  MessageSquareText,
  Settings,
  HelpCircle,
  Info,
  Search,
  Bell,
  Command,
  LogOut,
  X,
  Save,
  Loader2,
  ArrowRight,
  ScanSearch,
  UserRound,
} from "lucide-react";
import { Logo } from "@/components/aibi/atmosphere";
import { History } from "lucide-react";
import {
  AibiApi,
  clearAuth,
  getSessionId,
  type NotificationItem,
  type UserSettings,
} from "@/lib/aibi-api";

export const Route = createFileRoute("/app")({
  component: AppShell,
});

const nav: { to: string; label: string; icon: typeof Upload; live?: boolean }[] = [
  { to: "/app/upload", label: "Upload Data", icon: Upload },
  { to: "/app/dashboard", label: "Dashboard", icon: BarChart3, live: true },
  { to: "/app/xray", label: "Data X-Ray", icon: ScanSearch },
  { to: "/app/chat", label: "AI Chat", icon: MessageSquareText },
  { to: "/info", label: "About", icon: Info },
  // In sidebar nav items, add:
  { to: "/app/sessions", icon: History, label: "History" },
  { to: "/app/profile", icon: UserRound, label: "Profile" },
];

type AppPath = "/app/upload" | "/app/dashboard" | "/app/xray" | "/app/chat" | "/app/sessions" | "/app/profile";

function AppShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [userSettings, setUserSettings] = useState<UserSettings | null>(null);
  const sessionId = getSessionId();
  const active = nav.find((n) => pathname.startsWith(n.to))?.to ?? "/app/upload";
  const crumb = nav.find((n) => n.to === active)?.label ?? "App";

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen((open) => !open);
      }
      if (event.key === "Escape") setCommandOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    let mounted = true;
    AibiApi.settings().then((settings) => {
      if (mounted) setUserSettings(settings);
    }).catch(() => {});
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (!notificationsOpen || !sessionId) return;
    let mounted = true;
    const loadNotifications = async () => {
      try {
        const items = await AibiApi.notifications(sessionId);
        if (mounted) setNotifications(items);
      } catch {}
    };
    loadNotifications();
    const timer = window.setInterval(loadNotifications, 5000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [notificationsOpen, sessionId]);

  return (
    <div className="min-h-screen flex" style={{ background: "#080810", color: "#f1f5f9" }}>
      {/* Sidebar */}
      <aside
        className="w-[220px] shrink-0 sticky top-0 h-screen flex flex-col"
        style={{
          background: "rgba(10,10,18,0.95)",
          borderRight: "1px solid rgba(255,255,255,0.07)",
        }}
      >
        <Link to="/" className="px-5 py-5 block">
          <Logo />
        </Link>

        <nav className="px-3 mt-2 space-y-0.5">
          {nav.map((n) => {
            const isActive = pathname.startsWith(n.to);
            return (
              <Link
                key={n.to}
                to={n.to as any}
                className={`relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${isActive ? "text-white" : "text-white/55 hover:text-white hover:bg-white/5"}`}
              >
                {isActive && (
                  <motion.span
                    layoutId="sidebar-active"
                    className="absolute inset-0 rounded-xl"
                    style={{
                      background:
                        "linear-gradient(90deg, rgba(124,58,237,0.18), rgba(37,99,235,0.06))",
                      border: "1px solid rgba(124,58,237,0.25)",
                    }}
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <n.icon className="relative h-4 w-4 shrink-0" />
                <span className="relative flex-1">{n.label}</span>
                {n.live && (
                  <span
                    className="relative text-[9px] font-bold tracking-widest px-1.5 py-0.5 rounded"
                    style={{
                      background: "rgba(16,185,129,0.15)",
                      color: "#34d399",
                      border: "1px solid rgba(16,185,129,0.25)",
                    }}
                  >
                    LIVE
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto px-3 pb-3 space-y-0.5">
          <button
            onClick={() => setSettingsOpen(true)}
            className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:text-white hover:bg-white/5 transition"
          >
            <Settings className="h-4 w-4" /> Settings
          </button>
          <button className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:text-white hover:bg-white/5 transition">
            <HelpCircle className="h-4 w-4" /> Help
          </button>
          <button
            disabled={loggingOut}
            onClick={async () => {
              setLoggingOut(true);
              try {
                await AibiApi.logout();
              } catch {}
              clearAuth();
              navigate({ to: "/sign-in" });
            }}
            className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-white/55 hover:text-red-300 hover:bg-white/5 transition disabled:opacity-50"
          >
            {loggingOut ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <LogOut className="h-4 w-4" />
            )}
            Log out
          </button>
          <div
            className="mt-3 flex items-center gap-2 rounded-lg px-3 py-2 text-[11px] text-white/50"
            style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <span className="relative flex h-2 w-2">
              <span
                className="absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping"
                style={{ background: "#10b981" }}
              />
              <span
                className="relative inline-flex rounded-full h-2 w-2"
                style={{ background: "#10b981" }}
              />
            </span>
            API Connected · Port 8000
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header
          className="h-16 sticky top-0 z-20 flex items-center gap-4 px-6"
          style={{
            background: "rgba(8,8,16,0.85)",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            backdropFilter: "blur(20px)",
          }}
        >
          <div className="text-sm flex items-center gap-2 text-white/45">
            <span>Platform</span>
            <span className="text-white/20">›</span>
            <span className="text-white">{crumb}</span>
          </div>
          <div className="flex-1" />
          <button
            onClick={() => setCommandOpen(true)}
            className="hidden md:flex items-center gap-2 rounded-full px-3.5 py-2 text-xs text-white/50 hover:text-white"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <Search className="h-3.5 w-3.5" />
            <span>Search</span>
            <span className="flex items-center gap-1 ml-2 border border-white/10 rounded px-1.5 py-0.5 text-[10px]">
              <Command className="h-2.5 w-2.5" />K
            </span>
          </button>
          <div className="relative">
            <button
              aria-label="Notifications"
              onClick={() => setNotificationsOpen((open) => !open)}
              className="relative p-2 rounded-lg text-white/60 hover:text-white hover:bg-white/5"
            >
              <Bell className="h-4 w-4" />
              {notifications.some((notification) => !notification.read) && (
                <span
                  className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full"
                  style={{ background: "#a78bfa" }}
                />
              )}
            </button>
            {notificationsOpen && (
              <NotificationPanel
                notifications={notifications}
                onMarkRead={async () => {
                  if (sessionId) await AibiApi.markNotificationsRead(sessionId);
                  setNotifications((items) => items.map((item) => ({ ...item, read: true })));
                }}
              />
            )}
          </div>
          <Link
            to="/app/profile"
            aria-label="Open profile"
            title="Profile"
            className="grid h-8 w-8 place-items-center rounded-full text-xs font-semibold text-white"
            style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb)", boxShadow: "0 0 16px -4px rgba(124,58,237,0.6)" }}
          >
            {userSettings?.full_name?.trim()?.[0]?.toUpperCase() ?? "B"}
          </Link>
        </header>

        <main className="flex-1 min-w-0">
          <Outlet />
        </main>
      </div>
      {settingsOpen && (
        <SettingsModal onClose={() => setSettingsOpen(false)} onSaved={setUserSettings} />
      )}
      <AnimatePresence>
        {commandOpen && (
          <CommandPalette
            onClose={() => setCommandOpen(false)}
            onNavigate={(to) => {
              setCommandOpen(false);
              navigate({ to });
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

function CommandPalette({
  onClose,
  onNavigate,
}: {
  onClose: () => void;
  onNavigate: (to: AppPath) => void;
}) {
  const [query, setQuery] = useState("");
  const commands = [
    { label: "Upload data", hint: "Start a new workspace", to: "/app/upload", icon: Upload },
    {
      label: "Open dashboard",
      hint: "Review KPIs and charts",
      to: "/app/dashboard",
      icon: BarChart3,
    },
    {
      label: "Inspect dataset",
      hint: "Explore fields, quality, and relationships",
      to: "/app/xray",
      icon: ScanSearch,
    },
    {
      label: "Ask AI",
      hint: "Explore your data in plain English",
      to: "/app/chat",
      icon: MessageSquareText,
    },
    {
      label: "View history",
      hint: "Return to a previous session",
      to: "/app/sessions",
      icon: History,
    },
    {
      label: "Open profile",
      hint: "View your account and workspace activity",
      to: "/app/profile",
      icon: UserRound,
    },
  ] as const;
  const filtered = commands.filter((command) =>
    `${command.label} ${command.hint}`.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[60] bg-black/65 px-4 pt-[12vh] backdrop-blur-md"
      onMouseDown={onClose}
    >
      <motion.div
        initial={{ opacity: 0, y: -18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -12, scale: 0.98 }}
        transition={{ type: "spring", stiffness: 360, damping: 28 }}
        className="mx-auto w-full max-w-xl overflow-hidden rounded-2xl shadow-2xl"
        style={{
          background: "linear-gradient(180deg, rgba(29,28,46,0.98), rgba(13,13,24,0.98))",
          border: "1px solid rgba(255,255,255,0.12)",
        }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-white/[0.08] px-4">
          <Search className="h-4 w-4 text-violet-300" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Jump to a workspace view..."
            className="h-14 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/35"
          />
          <kbd className="rounded-md border border-white/10 px-2 py-1 text-[10px] text-white/35">
            ESC
          </kbd>
        </div>
        <div className="p-2">
          {filtered.length ? (
            filtered.map((command) => (
              <button
                key={command.to}
                onClick={() => onNavigate(command.to)}
                className="group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-violet-400/10"
              >
                <span className="grid h-9 w-9 place-items-center rounded-lg bg-white/[0.06] text-violet-200 group-hover:bg-violet-400/15">
                  <command.icon className="h-4 w-4" />
                </span>
                <span className="flex-1">
                  <span className="block text-sm text-white/90">{command.label}</span>
                  <span className="mt-0.5 block text-xs text-white/35">{command.hint}</span>
                </span>
                <ArrowRight className="h-4 w-4 text-white/20 group-hover:text-violet-300" />
              </button>
            ))
          ) : (
            <div className="px-3 py-10 text-center text-sm text-white/35">No matching view</div>
          )}
        </div>
        <div className="flex items-center gap-2 border-t border-white/[0.06] px-4 py-3 text-[10px] uppercase tracking-widest text-white/25">
          <Command className="h-3 w-3" /> Navigate your workspace
        </div>
      </motion.div>
    </motion.div>
  );
}

function NotificationPanel({
  notifications,
  onMarkRead,
}: {
  notifications: NotificationItem[];
  onMarkRead: () => void;
}) {
  return (
    <div
      className="absolute right-0 top-11 z-40 w-80 rounded-xl p-3 shadow-2xl"
      style={{ background: "#151522", border: "1px solid rgba(255,255,255,0.1)" }}
    >
      <div className="flex items-center justify-between px-2 py-1">
        <h2 className="text-sm font-semibold text-white">Notifications</h2>
        {notifications.some((notification) => !notification.read) && (
          <button onClick={onMarkRead} className="text-[11px] text-violet-300 hover:text-white">
            Mark all read
          </button>
        )}
      </div>
      <div className="mt-2 max-h-80 overflow-y-auto">
        {notifications.length === 0 ? (
          <p className="px-2 py-6 text-center text-xs text-white/40">
            No pipeline notifications yet.
          </p>
        ) : (
          notifications.map((notification) => (
            <div
              key={notification.id}
              className={`rounded-lg px-2 py-2.5 ${notification.read ? "" : "bg-white/[0.05]"}`}
            >
              <div className="text-xs font-medium text-white">{notification.title}</div>
              <div className="mt-1 text-[11px] leading-relaxed text-white/50">
                {notification.message}
              </div>
              {notification.created_at && (
                <div className="mt-1 text-[10px] text-white/30">{notification.created_at}</div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function SettingsModal({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (settings: UserSettings) => void;
}) {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let mounted = true;
    AibiApi.settings()
      .then((value) => {
        if (mounted) setSettings(value);
      })
      .catch(() => {
        if (mounted) setLoadError(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const update = (change: Partial<UserSettings>) =>
    setSettings((current) => (current ? { ...current, ...change } : current));

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    setMessage(null);
    try {
      const saved = await AibiApi.updateSettings(settings);
      localStorage.setItem("aibi_settings", JSON.stringify(saved));
      window.dispatchEvent(new CustomEvent("aibi-settings-updated", { detail: saved }));
      onSaved(saved);
      setSettings(saved);
      setMessage("Settings saved.");
    } catch {
      setMessage("Could not save settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/70 px-4 py-6"
      onMouseDown={onClose}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        className="w-full max-w-lg max-h-[calc(100vh-3rem)] overflow-y-auto rounded-2xl p-6"
        style={{ background: "#141420", border: "1px solid rgba(255,255,255,0.1)" }}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 id="settings-title" className="text-lg font-semibold text-white">
              Settings
            </h2>
            <p className="mt-1 text-xs text-white/45">Personalize your workspace and dashboard.</p>
          </div>
          <button
            aria-label="Close settings"
            onClick={onClose}
            className="p-2 text-white/50 hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {loadError ? (
          <div className="py-10 text-center text-sm text-red-300">
            Could not load settings. Please try again.
          </div>
        ) : settings ? (
          <div className="mt-6 space-y-6">
            <div>
              <h3 className="text-[11px] uppercase tracking-widest text-white/40">Profile</h3>
              <label className="mt-3 block text-sm text-white/75">
                Display name
                <input
                  value={settings.full_name}
                  onChange={(e) => update({ full_name: e.target.value })}
                  maxLength={120}
                  className="mt-1.5 w-full rounded-lg bg-white/10 px-3 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </label>
            </div>
            <div>
              <h3 className="text-[11px] uppercase tracking-widest text-white/40">Workspace</h3>
              <div className="mt-3 space-y-2">
                <SettingToggle
                  label="Show executive brief"
                  description="Generate a plain-language overview above dashboard KPIs."
                  checked={settings.show_executive_summary}
                  onChange={(checked) => update({ show_executive_summary: checked })}
                />
                <SettingToggle
                  label="Show AI explanations"
                  description="Display plain-language findings below charts."
                  checked={settings.show_insights}
                  onChange={(checked) => update({ show_insights: checked })}
                />
              </div>
            </div>
            <div>
              <h3 className="text-[11px] uppercase tracking-widest text-white/40">Dashboard defaults</h3>
              <label className="mt-3 block text-sm text-white/75">
                Default date window
                <select
                  value={settings.default_date_range}
                  onChange={(event) => update({ default_date_range: event.target.value as UserSettings["default_date_range"] })}
                  className="mt-1.5 w-full rounded-lg bg-white/10 px-3 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500/50"
                >
                  <option value="all">All available dates</option>
                  <option value="30d">Last 30 days</option>
                  <option value="90d">Last 90 days</option>
                  <option value="12m">Last 12 months</option>
                </select>
              </label>
              <label className="mt-4 block text-sm text-white/75">
                KPI number display
                <select
                  value={settings.number_format}
                  onChange={(event) => update({ number_format: event.target.value as UserSettings["number_format"] })}
                  className="mt-1.5 w-full rounded-lg bg-white/10 px-3 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500/50"
                >
                  <option value="compact">Compact (1.2K)</option>
                  <option value="full">Exact (1,234)</option>
                </select>
              </label>
            </div>
          </div>
        ) : (
          <div className="py-10 text-center text-sm text-white/45">Loading settings...</div>
        )}
        <div className="mt-6 flex items-center justify-end gap-3">
          {message && <span className="mr-auto text-xs text-white/50">{message}</span>}
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-white/60 hover:text-white"
          >
            Cancel
          </button>
          <button
            disabled={!settings || saving || !settings?.full_name.trim()}
            onClick={save}
            className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving..." : "Save changes"}
          </button>
        </div>
      </section>
    </div>
  );
}

function SettingToggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl px-3 py-3 hover:bg-white/[0.04]">
      <span>
        <span className="block text-sm text-white/80">{label}</span>
        <span className="mt-0.5 block text-xs text-white/40">{description}</span>
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 shrink-0 accent-violet-500"
      />
    </label>
  );
}
