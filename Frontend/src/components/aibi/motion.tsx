import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useScroll,
  useSpring,
  useTransform,
  type Variants,
} from "framer-motion";
import { useRouterState } from "@tanstack/react-router";
import logoAsset from "@/assets/aibi-logo-transparent.png.asset.json";

/* ---------- Cinematic first-load curtain ---------- */
export function CinematicLoader() {
  const [mounted, setMounted] = useState(false);
  const [done, setDone] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    setMounted(true);
    let p = 0;
    const iv = setInterval(() => {
      p = Math.min(100, p + (100 - p) * 0.18 + 2);
      setProgress(p);
      if (p >= 99.5) {
        clearInterval(iv);
        setTimeout(() => setDone(true), 350);
      }
    }, 80);
    return () => clearInterval(iv);
  }, []);

  if (!mounted) return null;

  return (
    <AnimatePresence>
      {!done && (
        <motion.div
          key="loader"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.05, filter: "blur(12px)" }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="fixed inset-0 z-[200] grid place-items-center overflow-hidden"
          style={{ background: "#050509" }}
        >
          {/* aurora backdrop */}
          <div className="pointer-events-none absolute inset-0 opacity-80">
            <div
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(50% 45% at 50% 45%, rgba(124,58,237,0.35), transparent 65%), radial-gradient(45% 40% at 70% 30%, rgba(37,99,235,0.25), transparent 70%), radial-gradient(40% 40% at 30% 70%, rgba(8,145,178,0.22), transparent 70%)",
                filter: "blur(30px)",
              }}
            />
          </div>

          <div className="relative z-10 flex flex-col items-center gap-8">
            <motion.div
              initial={{ scale: 0.85, opacity: 0 }}
              animate={{
                scale: [0.95, 1.02, 0.98, 1],
                opacity: 1,
              }}
              transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              className="relative h-24 w-24 rounded-3xl grid place-items-center"
              style={{
                background:
                  "radial-gradient(circle at 30% 30%, rgba(124,58,237,0.5), rgba(37,99,235,0.2) 60%, transparent 80%)",
                boxShadow:
                  "0 0 80px -10px rgba(124,58,237,0.75), inset 0 0 0 1px rgba(255,255,255,0.08)",
              }}
            >
              <img src={logoAsset.url} alt="AIBI Nexus" className="h-16 w-16 object-contain" />
              <motion.span
                aria-hidden
                className="absolute inset-0 rounded-3xl"
                animate={{ opacity: [0.4, 0.9, 0.4] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                style={{ boxShadow: "0 0 60px 4px rgba(167,139,250,0.35)" }}
              />
            </motion.div>

            <div className="flex flex-col items-center gap-3">
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15, duration: 0.6 }}
                className="text-2xl font-semibold tracking-tight font-display text-white"
              >
                AIBI <span className="text-white/50 font-normal">Nexus</span>
              </motion.div>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.35 }}
                className="text-[10px] uppercase tracking-[0.4em] text-white/40"
              >
                Calibrating neural mesh
              </motion.div>
            </div>

            <div className="relative h-[3px] w-[280px] overflow-hidden rounded-full bg-white/5">
              <motion.div
                className="absolute inset-y-0 left-0 rounded-full"
                style={{
                  width: `${progress}%`,
                  background:
                    "linear-gradient(90deg, #7c3aed, #2563eb 60%, #67e8f9)",
                  boxShadow: "0 0 18px rgba(124,58,237,0.9)",
                }}
                transition={{ ease: "easeOut" }}
              />
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ---------- Route change transition ---------- */
export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 14, filter: "blur(10px)" }}
        animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
        exit={{ opacity: 0, y: -8, filter: "blur(10px)" }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        style={{ minHeight: "100vh" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/* ---------- Top scroll progress ---------- */
export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 22, mass: 0.3 });
  return (
    <motion.div
      aria-hidden
      className="fixed left-0 right-0 top-0 z-[150] h-[2px] origin-left"
      style={{
        scaleX,
        background: "linear-gradient(90deg, #7c3aed, #2563eb, #67e8f9)",
        boxShadow: "0 0 14px rgba(124,58,237,0.8), 0 0 4px rgba(103,232,249,0.9)",
      }}
    />
  );
}

/* ---------- Scroll reveal ---------- */
const revealVariants: Variants = {
  hidden: { opacity: 0, y: 28, filter: "blur(6px)" },
  visible: { opacity: 1, y: 0, filter: "blur(0px)" },
};
export function Reveal({
  children,
  delay = 0,
  className,
  as: As = "div",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  as?: any;
}) {
  const MotionAs = motion(As);
  return (
    <MotionAs
      className={className}
      variants={revealVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </MotionAs>
  );
}

export function StaggerGroup({
  children,
  className,
  stagger = 0.08,
}: {
  children: ReactNode;
  className?: string;
  stagger?: number;
}) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-60px" }}
      variants={{ visible: { transition: { staggerChildren: stagger } } }}
    >
      {children}
    </motion.div>
  );
}

export const StaggerItem = motion.div;
export const staggerItemVariants: Variants = revealVariants;

/* ---------- Parallax wrapper (transforms child on scroll) ---------- */
export function Parallax({
  children,
  offset = 60,
  className,
}: {
  children: ReactNode;
  offset?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [offset, -offset]);
  return (
    <motion.div ref={ref} className={className} style={{ y }}>
      {children}
    </motion.div>
  );
}

/* ---------- Magnetic button ---------- */
export function MagneticButton({
  children,
  className,
  strength = 0.35,
  ...rest
}: React.ComponentProps<typeof motion.button> & { strength?: number }) {
  const ref = useRef<HTMLButtonElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 260, damping: 18 });
  const sy = useSpring(y, { stiffness: 260, damping: 18 });

  return (
    <motion.button
      ref={ref}
      style={{ x: sx, y: sy }}
      onMouseMove={(e) => {
        const r = ref.current?.getBoundingClientRect();
        if (!r) return;
        x.set((e.clientX - (r.left + r.width / 2)) * strength);
        y.set((e.clientY - (r.top + r.height / 2)) * strength);
      }}
      onMouseLeave={() => {
        x.set(0);
        y.set(0);
      }}
      className={className}
      {...rest}
    >
      {children}
    </motion.button>
  );
}
