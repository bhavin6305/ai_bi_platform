import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Upload, Database, BarChart3, MessageSquareText, ArrowRight, Sparkles } from "lucide-react";
import { Logo } from "@/components/aibi/atmosphere";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AIBI Platform — Business intelligence that thinks for itself" },
      { name: "description", content: "Upload data. Get auto-detected schemas, ETL, dashboards, and an AI analyst — in under a minute." },
    ],
  }),
  component: Landing,
});

const stats = [
  { v: "< 60s", l: "From upload to dashboard" },
  { v: "7", l: "Semantic types detected" },
  { v: "100%", l: "Open source AI" },
  { v: "∞", l: "Business datasets" },
];

const features = [
  { icon: Upload, title: "Upload anything", desc: "CSV, Excel, ZIPs — up to hundreds of MB. We handle messy data.", tint: "#7c3aed" },
  { icon: Database, title: "Auto ETL", desc: "Schema inference, type detection, and relationship discovery in seconds.", tint: "#2563eb" },
  { icon: BarChart3, title: "Instant dashboards", desc: "KPIs, charts, and insights auto-generated for your dataset.", tint: "#0891b2" },
  { icon: MessageSquareText, title: "Ask in English", desc: "Natural-language questions turn into SQL, answers, and evidence.", tint: "#10b981" },
];

function Landing() {
  return (
    <div className="relative min-h-screen overflow-hidden" style={{ background: "#080810" }}>
      {/* radial glow */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[900px]"
           style={{ background: "radial-gradient(60% 55% at 50% 0%, rgba(124,58,237,0.28), transparent 65%), radial-gradient(50% 40% at 80% 10%, rgba(37,99,235,0.18), transparent 70%), radial-gradient(40% 40% at 15% 20%, rgba(8,145,178,0.15), transparent 70%)" }} />
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-30 [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]" />

      {/* Nav */}
      <header className="relative z-10 max-w-7xl mx-auto flex items-center justify-between px-6 py-5">
        <Logo />
        <nav className="hidden md:flex items-center gap-8 text-sm text-white/60">
          <a className="hover:text-white transition" href="#features">Features</a>
          <a className="hover:text-white transition" href="#stats">Platform</a>
          <Link className="hover:text-white transition" to="/info">About</Link>
          <a className="hover:text-white transition" href="https://github.com" target="_blank" rel="noreferrer">Open source</a>
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/sign-in" className="hidden sm:inline-flex text-sm text-white/70 hover:text-white transition rounded-full px-4 py-2">
            Sign in
          </Link>
          <Link to="/sign-up" className="btn-gradient text-sm rounded-full px-4 py-2 font-medium">
            Get started
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative z-10 max-w-6xl mx-auto text-center px-6 pt-20 pb-24">
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3.5 py-1.5 text-[11px] uppercase tracking-widest text-white/60 backdrop-blur">
          AI Business Intelligence · v1.0
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.1 }}
          className="mt-8 text-5xl md:text-7xl font-semibold tracking-tight leading-[1.05] text-white">
          Business intelligence
          <br />
          <span style={{ background: "linear-gradient(135deg,#c4b5fd,#93c5fd,#67e8f9)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            that thinks for itself.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 0.3 }}
          className="mt-6 max-w-2xl mx-auto text-lg text-white/50 leading-relaxed">
          Drop a spreadsheet. AIBI auto-detects schemas, runs the ETL pipeline, generates
          dashboards, and lets you chat with your data in plain English.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.45 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <Link to="/app/upload" className="group inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white transition"
                style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 10px 40px -8px rgba(124,58,237,0.5)" }}>
            <Upload className="h-4 w-4" /> Upload your data
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
          <Link to="/app/dashboard" className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-6 py-3 text-sm font-medium text-white/80 hover:bg-white/10 transition">
            View demo
          </Link>
        </motion.div>

        {/* Stats */}
        <motion.div
          id="stats"
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.6 }}
          className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-px rounded-2xl overflow-hidden border border-white/8"
          style={{ background: "rgba(255,255,255,0.05)" }}>
          {stats.map((s) => (
            <div key={s.l} className="px-6 py-8 text-left" style={{ background: "rgba(13,13,24,0.9)" }}>
              <div className="text-3xl md:text-4xl font-semibold tracking-tight text-white">{s.v}</div>
              <div className="mt-2 text-xs uppercase tracking-widest text-white/40">{s.l}</div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 max-w-6xl mx-auto px-6 pb-32">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.6, delay: i * 0.08 }}
              className="group relative rounded-2xl p-6 overflow-hidden"
              style={{ background: "rgba(13,13,24,0.9)", border: "1px solid rgba(255,255,255,0.07)" }}>
              <div className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 group-hover:opacity-100 transition duration-500"
                   style={{ background: `radial-gradient(400px circle at 50% 0%, ${f.tint}33, transparent 60%)` }} />
              <div className="relative">
                <div className="h-10 w-10 rounded-xl grid place-items-center" style={{ background: `linear-gradient(135deg, ${f.tint}, transparent)`, boxShadow: `0 0 24px -6px ${f.tint}80` }}>
                  <f.icon className="h-5 w-5 text-white" />
                </div>
                <h3 className="mt-4 text-[15px] font-semibold text-white">{f.title}</h3>
                <p className="mt-1.5 text-sm text-white/50 leading-relaxed">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-24 text-center">
          <Link to="/app/upload" className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white"
                style={{ background: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2)", boxShadow: "0 10px 40px -8px rgba(124,58,237,0.5)" }}>
            Start with your first dataset <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
