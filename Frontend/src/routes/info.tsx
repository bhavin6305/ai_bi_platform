import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  Sparkles, Cpu, Database, ShieldCheck, Rocket, Users,
  ArrowRight, Github, LineChart, Wand2,
} from "lucide-react";
import { Logo } from "@/components/aibi/atmosphere";
import {
  Reveal,
  StaggerGroup,
  StaggerItem,
  staggerItemVariants,
  Parallax,
  MagneticButton,
} from "@/components/aibi/motion";

export const Route = createFileRoute("/info")({
  head: () => ({
    meta: [
      { title: "Our Story & Vision — AIBI Nexus" },
      { name: "description", content: "The story, principles, and roadmap behind AIBI Nexus — an AI-native business intelligence platform built for teams that move fast." },
      { property: "og:title", content: "Our Story & Vision — AIBI Nexus" },
      { property: "og:description", content: "How AIBI Nexus reimagines business intelligence with AI-native workflows, cinematic UX, and open architecture." },
    ],
  }),
  component: InfoPage,
});

const highlights = [
  { icon: Cpu, title: "AI-native core", desc: "Every workflow — schema, ETL, dashboards, chat — is authored by models, not templates.", tint: "#7c3aed" },
  { icon: Database, title: "Any data source", desc: "CSV, Excel, ZIPs, warehouses. We infer semantics, not just types.", tint: "#2563eb" },
  { icon: LineChart, title: "Instant insight", desc: "From upload to a live dashboard in under a minute — on any dataset.", tint: "#0891b2" },
  { icon: ShieldCheck, title: "Private by default", desc: "Your data stays yours. Runs local or in your own cloud with zero telemetry.", tint: "#10b981" },
  { icon: Wand2, title: "Cinematic UX", desc: "Every interaction — from load to hover — is designed with intention and motion.", tint: "#f59e0b" },
  { icon: Users, title: "Built with teams", desc: "Shipped alongside analysts, PMs, and founders who live inside dashboards.", tint: "#ec4899" },
];

const stats = [
  { v: "< 60s", l: "Data → dashboard" },
  { v: "12+", l: "Chart primitives" },
  { v: "100%", l: "Open architecture" },
  { v: "0", l: "Config required" },
];

const timeline = [
  { year: "2023", title: "The spark", desc: "A prototype answering analyst questions from a raw CSV — no schema, no setup." },
  { year: "2024", title: "Neural mesh", desc: "Semantic type detection, auto-ETL, and streaming SQL generation land in one engine." },
  { year: "2025", title: "AIBI Nexus", desc: "Cinematic BI shell, live chat analyst, and open dashboards ship to early teams." },
  { year: "2026", title: "The platform", desc: "Extensible connectors, agent workflows, and collaborative canvases for every function." },
];

function InfoPage() {
  return (
    <div className="relative min-h-screen overflow-hidden" style={{ background: "#080810", color: "#f1f5f9" }}>
      {/* parallax ambient glow */}
      <Parallax offset={120} className="pointer-events-none absolute inset-x-0 -top-40 h-[900px]">
        <div
          className="h-full w-full"
          style={{
            background:
              "radial-gradient(55% 55% at 50% 0%, rgba(124,58,237,0.35), transparent 65%), radial-gradient(45% 40% at 80% 10%, rgba(37,99,235,0.22), transparent 70%), radial-gradient(40% 40% at 15% 20%, rgba(8,145,178,0.18), transparent 70%)",
          }}
        />
      </Parallax>
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-25 [mask-image:radial-gradient(ellipse_at_top,black_20%,transparent_70%)]" />

      {/* Nav */}
      <header className="relative z-10 max-w-7xl mx-auto flex items-center justify-between px-6 py-5">
        <Link to="/"><Logo /></Link>
        <nav className="hidden md:flex items-center gap-8 text-sm text-white/60">
          <Link className="hover:text-white transition" to="/">Home</Link>
          <Link className="hover:text-white transition" to="/info">About</Link>
          <a className="hover:text-white transition" href="https://github.com" target="_blank" rel="noreferrer">Open source</a>
        </nav>
        <Link to="/app/upload" className="btn-gradient btn-press text-sm rounded-full px-4 py-2 font-medium">
          Launch app
        </Link>
      </header>

      {/* Hero */}
      <section className="relative z-10 max-w-5xl mx-auto text-center px-6 pt-16 pb-24">
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3.5 py-1.5 text-[11px] uppercase tracking-widest text-white/60 backdrop-blur">
           Our story · Vision · Principles
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.1 }}
          className="mt-8 text-5xl md:text-7xl font-semibold tracking-tight leading-[1.05] text-white font-display">
          Our Story
          <br />
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage: "linear-gradient(120deg,#c4b5fd,#93c5fd,#67e8f9,#c4b5fd)",
              backgroundSize: "200% 100%",
              animation: "gradient-pan 6s ease infinite",
              WebkitBackgroundClip: "text",
            }}
          >
            & Vision.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.9, delay: 0.35 }}
          className="mt-6 max-w-2xl mx-auto text-lg text-white/55 leading-relaxed">
          AIBI Nexus is a rebuild of business intelligence around a simple idea: the analyst
          should be an AI, and the interface should feel like a film — considered, ambient, alive.
        </motion.p>
      </section>

      {/* Stats strip */}
      <section className="relative z-10 max-w-6xl mx-auto px-6">
        <StaggerGroup className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((s) => (
            <StaggerItem
              key={s.l}
              variants={staggerItemVariants}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="card-glass p-6 text-center"
            >
              <div className="text-3xl font-semibold font-display text-white">{s.v}</div>
              <div className="mt-1 text-[11px] uppercase tracking-widest text-white/45">{s.l}</div>
            </StaggerItem>
          ))}
        </StaggerGroup>
      </section>

      {/* Highlight cards */}
      <section className="relative z-10 max-w-6xl mx-auto px-6 pt-28">
        <Reveal>
          <div className="text-center mb-14">
            <div className="text-[11px] uppercase tracking-[0.35em] text-white/40">What we believe</div>
            <h2 className="mt-3 text-3xl md:text-5xl font-semibold tracking-tight font-display">
              Principles that shape every pixel.
            </h2>
          </div>
        </Reveal>

        <StaggerGroup className="grid md:grid-cols-2 lg:grid-cols-3 gap-5" stagger={0.09}>
          {highlights.map((h) => (
            <StaggerItem
              key={h.title}
              variants={staggerItemVariants}
              transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
              className="card-glass p-6 relative overflow-hidden group"
            >
              <div
                className="absolute -top-16 -right-16 h-40 w-40 rounded-full blur-3xl opacity-40 group-hover:opacity-70 transition-opacity"
                style={{ background: `radial-gradient(circle, ${h.tint}, transparent 70%)` }}
              />
              <div
                className="relative h-11 w-11 rounded-xl grid place-items-center"
                style={{ background: `${h.tint}20`, border: `1px solid ${h.tint}40` }}
              >
                <h.icon className="h-5 w-5" style={{ color: h.tint }} />
              </div>
              <div className="relative mt-5 text-lg font-semibold text-white">{h.title}</div>
              <p className="relative mt-2 text-sm text-white/55 leading-relaxed">{h.desc}</p>
            </StaggerItem>
          ))}
        </StaggerGroup>
      </section>

      {/* Timeline */}
      <section className="relative z-10 max-w-4xl mx-auto px-6 pt-32 pb-24">
        <Reveal>
          <div className="text-center mb-16">
            <div className="text-[11px] uppercase tracking-[0.35em] text-white/40">The journey</div>
            <h2 className="mt-3 text-3xl md:text-5xl font-semibold tracking-tight font-display">
              From a spark to a platform.
            </h2>
          </div>
        </Reveal>

        <div className="relative pl-8 md:pl-0">
          {/* glowing spine */}
          <div className="absolute left-3 md:left-1/2 top-0 bottom-0 w-px md:-translate-x-1/2">
            <div className="absolute inset-0 bg-white/5" />
            <motion.div
              initial={{ scaleY: 0 }}
              whileInView={{ scaleY: 1 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0 origin-top"
              style={{
                background: "linear-gradient(180deg,#7c3aed,#2563eb,#67e8f9)",
                boxShadow: "0 0 16px rgba(124,58,237,0.75)",
              }}
            />
          </div>

          <div className="space-y-14">
            {timeline.map((t, i) => {
              const left = i % 2 === 0;
              return (
                <Reveal key={t.year} delay={i * 0.08}>
                  <div className={`relative md:grid md:grid-cols-2 md:gap-10 items-center ${left ? "" : "md:[direction:rtl]"}`}>
                    {/* dot */}
                    <div className="absolute -left-[5px] md:left-1/2 md:-translate-x-1/2 top-2 md:top-6">
                      <span className="relative flex h-3 w-3">
                        <span className="absolute inline-flex h-full w-full rounded-full opacity-70 animate-ping" style={{ background: "#a78bfa" }} />
                        <span
                          className="relative inline-flex rounded-full h-3 w-3"
                          style={{ background: "#c4b5fd", boxShadow: "0 0 14px #a78bfa" }}
                        />
                      </span>
                    </div>

                    <div className={`md:[direction:ltr] ${left ? "md:pr-10 md:text-right" : "md:pl-10"}`}>
                      <div className="card-glass p-6">
                        <div className="text-[11px] uppercase tracking-[0.3em] font-mono" style={{ color: "#a78bfa" }}>
                          {t.year}
                        </div>
                        <div className="mt-2 text-xl font-semibold text-white">{t.title}</div>
                        <p className="mt-2 text-sm text-white/55 leading-relaxed">{t.desc}</p>
                      </div>
                    </div>
                    <div />
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 pb-32">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl p-12 md:p-16 text-center card-glass">
            <div
              className="absolute inset-0 opacity-70"
              style={{
                background:
                  "radial-gradient(60% 80% at 50% 0%, rgba(124,58,237,0.35), transparent 70%), radial-gradient(50% 80% at 100% 100%, rgba(37,99,235,0.25), transparent 70%)",
              }}
            />
            <div className="relative">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3.5 py-1.5 text-[11px] uppercase tracking-widest text-white/60">
                <Rocket className="h-3 w-3" style={{ color: "#c4b5fd" }} /> Start free · 60 seconds
              </div>
              <h3 className="mt-6 text-4xl md:text-6xl font-semibold tracking-tight font-display text-white">
                Turn a spreadsheet
                <br />
                into a strategy.
              </h3>
              <p className="mt-4 max-w-xl mx-auto text-white/55">
                Launch AIBI Nexus, drop in your data, and let the neural mesh do the analysis.
              </p>

              <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
                <Link to="/app/upload">
                  <MagneticButton className="btn-gradient btn-press rounded-full px-7 py-3 text-sm font-semibold inline-flex items-center gap-2">
                    Launch the app <ArrowRight className="h-4 w-4" />
                  </MagneticButton>
                </Link>
                <MagneticButton
                  strength={0.25}
                  onClick={() => window.open("https://github.com", "_blank")}
                  className="rounded-full px-6 py-3 text-sm font-medium border border-white/10 bg-white/5 text-white/80 hover:text-white hover:bg-white/10 transition inline-flex items-center gap-2"
                >
                  <Github className="h-4 w-4" /> Star on GitHub
                </MagneticButton>
              </div>
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
