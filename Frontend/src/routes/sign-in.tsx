import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useState } from "react";
import { Mail, Lock, ArrowRight, Github, Chrome, Sparkles, Eye, EyeOff } from "lucide-react";
import { Logo } from "@/components/aibi/atmosphere";
import { AibiApi, setAuthToken } from "@/lib/aibi-api";

export const Route = createFileRoute("/sign-in")({
  head: () => ({
    meta: [
      { title: "Sign in — AIBI Nexus" },
      { name: "description", content: "Access your AI business analyst. Sign in to AIBI Nexus and turn data into decisions." },
      { property: "og:title", content: "Sign in — AIBI Nexus" },
      { property: "og:description", content: "Access your AI business analyst. Sign in to AIBI Nexus." },
    ],
  }),
  component: SignInPage,
});

function SignInPage() {
  return <AuthScreen mode="sign-in" />;
}

export function AuthScreen({ mode }: { mode: "sign-in" | "sign-up" }) {
  const isSignUp = mode === "sign-up";
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget as HTMLFormElement);
    setLoading(true);
    setError(null);
    try {
      const response = isSignUp
        ? await AibiApi.signup(
            String(formData.get("full_name") || ""),
            String(formData.get("email") || ""),
            String(formData.get("password") || ""),
          )
        : await AibiApi.signin(
            String(formData.get("email") || ""),
            String(formData.get("password") || ""),
          );
      setAuthToken(response.access_token);
      navigate({ to: "/app/upload" });
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || "Authentication failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden" style={{ background: "#050509" }}>
      {/* Cinematic aurora backdrop */}
      <div className="pointer-events-none absolute inset-0">
        <motion.div
          className="absolute inset-0"
          animate={{
            background: [
              "radial-gradient(50% 45% at 30% 30%, rgba(124,58,237,0.35), transparent 65%), radial-gradient(45% 40% at 75% 25%, rgba(37,99,235,0.28), transparent 70%), radial-gradient(40% 40% at 50% 80%, rgba(8,145,178,0.22), transparent 70%)",
              "radial-gradient(50% 45% at 70% 40%, rgba(124,58,237,0.38), transparent 65%), radial-gradient(45% 40% at 25% 65%, rgba(37,99,235,0.30), transparent 70%), radial-gradient(40% 40% at 60% 20%, rgba(8,145,178,0.24), transparent 70%)",
              "radial-gradient(50% 45% at 30% 30%, rgba(124,58,237,0.35), transparent 65%), radial-gradient(45% 40% at 75% 25%, rgba(37,99,235,0.28), transparent 70%), radial-gradient(40% 40% at 50% 80%, rgba(8,145,178,0.22), transparent 70%)",
            ],
          }}
          transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
          style={{ filter: "blur(20px)" }}
        />
        <div className="absolute inset-0 bg-grid opacity-[0.06]" />
        <motion.div
          aria-hidden
          className="absolute -top-40 -left-40 h-[500px] w-[500px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(167,139,250,0.35), transparent 70%)", filter: "blur(60px)" }}
          animate={{ x: [0, 60, -30, 0], y: [0, 40, -20, 0] }}
          transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          aria-hidden
          className="absolute -bottom-40 -right-40 h-[600px] w-[600px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(103,232,249,0.28), transparent 70%)", filter: "blur(70px)" }}
          animate={{ x: [0, -50, 30, 0], y: [0, -40, 20, 0] }}
          transition={{ duration: 26, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      {/* Top bar */}
      <header className="relative z-10 max-w-7xl mx-auto flex items-center justify-between px-6 py-6">
        <Link to="/"><Logo /></Link>
        <Link to={isSignUp ? "/sign-in" : "/sign-up"} className="text-sm text-white/60 hover:text-white transition">
          {isSignUp ? "Already have an account? Sign in" : "New here? Create an account"}
        </Link>
      </header>

      <main className="relative z-10 grid lg:grid-cols-2 gap-12 max-w-7xl mx-auto px-6 pt-8 pb-16">
        {/* Left – narrative */}
        <motion.section
          initial={{ opacity: 0, x: -20, filter: "blur(10px)" }}
          animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          className="hidden lg:flex flex-col justify-center gap-8"
        >
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3.5 py-1.5 text-[11px] uppercase tracking-widest text-white/60 backdrop-blur">
            
            {isSignUp ? "Start your free workspace" : "Welcome back"}
          </div>
          <h1 className="text-5xl xl:text-6xl font-semibold tracking-tight leading-[1.05] font-display text-white">
            {isSignUp ? (
              <>Meet the analyst<br /><span style={{ background: "linear-gradient(135deg,#c4b5fd,#93c5fd,#67e8f9)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>that never sleeps.</span></>
            ) : (
              <>Your data is<br /><span style={{ background: "linear-gradient(135deg,#c4b5fd,#93c5fd,#67e8f9)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>waiting for you.</span></>
            )}
          </h1>
          <p className="text-white/55 text-lg max-w-md leading-relaxed">
            {isSignUp
              ? "Spin up a workspace in seconds. Upload a spreadsheet. Get dashboards, forecasts, and answers — all before your coffee cools."
              : "Pick up where you left off. Your dashboards, chats, and pipelines are exactly where you saved them."}
          </p>

          <div className="flex flex-col gap-3 mt-2">
            {[
              "Auto ETL on any CSV or Excel file",
              "Real-time forecasts + anomaly detection",
              "Chat with your data in plain English",
            ].map((t, i) => (
              <motion.div
                key={t}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.1, duration: 0.6 }}
                className="flex items-center gap-3 text-sm text-white/70"
              >
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: "linear-gradient(90deg,#a78bfa,#67e8f9)", boxShadow: "0 0 10px rgba(167,139,250,0.8)" }} />
                {t}
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* Right – card */}
        <motion.section
          initial={{ opacity: 0, y: 24, filter: "blur(12px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          transition={{ duration: 0.9, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="flex items-center justify-center"
        >
          <div
            className="relative w-full max-w-md rounded-3xl p-8 md:p-10"
            style={{
              background: "linear-gradient(180deg, rgba(20,20,32,0.85), rgba(10,10,20,0.85))",
              border: "1px solid rgba(255,255,255,0.08)",
              boxShadow: "0 40px 120px -30px rgba(124,58,237,0.45), inset 0 1px 0 rgba(255,255,255,0.06)",
              backdropFilter: "blur(24px) saturate(140%)",
            }}
          >
            {/* animated border sheen */}
            <motion.div
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-3xl"
              style={{
                background: "linear-gradient(120deg, transparent 30%, rgba(167,139,250,0.25), transparent 70%)",
                mixBlendMode: "overlay",
              }}
              animate={{ backgroundPosition: ["0% 0%", "200% 0%"] }}
              transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
            />

            <div className="relative">
              <div className="lg:hidden mb-6"><Logo showWordmark={false} size={44} /></div>
              <h2 className="text-2xl font-semibold tracking-tight font-display text-white">
                {isSignUp ? "Create your account" : "Sign in to AIBI Nexus"}
              </h2>
              <p className="mt-1.5 text-sm text-white/50">
                {isSignUp ? "Free forever for personal projects." : "Enter your details to continue."}
              </p>

              {/* Social */}
              <div className="mt-7 grid grid-cols-2 gap-2.5">
                <SocialBtn icon={Chrome} label="Google" />
                <SocialBtn icon={Github} label="GitHub" />
              </div>

              <div className="my-6 flex items-center gap-3 text-[10px] uppercase tracking-[0.3em] text-white/30">
                <div className="h-px flex-1 bg-white/10" /> or <div className="h-px flex-1 bg-white/10" />
              </div>

              <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
                {isSignUp && (
                  <Field label="Full name" icon={<span className="text-xs text-white/40">Aa</span>}>
                    <input required name="full_name" type="text" placeholder="Jane Doe" className="auth-input" />
                  </Field>
                )}
                <Field label="Email" icon={<Mail className="h-4 w-4 text-white/40" />}>
                  <input required name="email" type="email" placeholder="you@company.com" className="auth-input" />
                </Field>
                <Field label="Password" icon={<Lock className="h-4 w-4 text-white/40" />}>
                  <input required name="password" type={showPw ? "text" : "password"} placeholder="••••••••" className="auth-input pr-10" />
                  <button type="button" onClick={() => setShowPw((v) => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/80">
                    {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </Field>

                {!isSignUp && (
                  <div className="flex items-center justify-between text-xs">
                    <label className="flex items-center gap-2 text-white/50">
                      <input type="checkbox" className="accent-violet-500 rounded" /> Remember me
                    </label>
                    <a href="#" className="text-white/60 hover:text-white transition">Forgot password?</a>
                  </div>
                )}

                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  disabled={loading}
                  type="submit"
                  className="mt-2 group relative inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white overflow-hidden disabled:opacity-70"
                  style={{
                    background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)",
                    boxShadow: "0 10px 40px -8px rgba(124,58,237,0.6)",
                  }}
                >
                  <motion.span
                    aria-hidden
                    className="absolute inset-0"
                    style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent)" }}
                    animate={{ x: ["-100%", "200%"] }}
                    transition={{ duration: 2.4, repeat: Infinity, ease: "linear" }}
                  />
                  <span className="relative">{loading ? "Loading…" : isSignUp ? "Create account" : "Sign in"}</span>
                  {!loading && <ArrowRight className="relative h-4 w-4 transition-transform group-hover:translate-x-0.5" />}
                </motion.button>

                {error && <p role="alert" className="text-xs text-red-300 text-center">{error}</p>}

                <p className="text-[11px] text-white/40 text-center mt-2">
                  By continuing you agree to our <a href="#" className="underline">Terms</a> and <a href="#" className="underline">Privacy Policy</a>.
                </p>
              </form>
            </div>
          </div>
        </motion.section>
      </main>

      <style>{`
        .auth-input {
          width: 100%;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 12px;
          padding: 11px 12px 11px 38px;
          font-size: 14px;
          color: #f1f5f9;
          outline: none;
          transition: border-color .2s, box-shadow .2s, background .2s;
        }
        .auth-input::placeholder { color: rgba(255,255,255,0.3); }
        .auth-input:focus {
          background: rgba(255,255,255,0.05);
          border-color: rgba(124,58,237,0.5);
          box-shadow: 0 0 0 4px rgba(124,58,237,0.12);
        }
      `}</style>
    </div>
  );
}

function Field({ label, icon, children }: { label: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[11px] uppercase tracking-widest text-white/40">{label}</span>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 grid place-items-center">{icon}</span>
        {children}
      </div>
    </label>
  );
}

function SocialBtn({ icon: Icon, label }: { icon: typeof Chrome; label: string }) {
  return (
    <motion.button
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.98 }}
      type="button"
      className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-white/80 hover:bg-white/[0.06] hover:border-white/20 transition"
    >
      <Icon className="h-4 w-4" /> {label}
    </motion.button>
  );
}
