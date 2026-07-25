import { type ReactNode } from "react";
import logoAsset from "@/assets/aibi-logo-transparent.png.asset.json";

export function AmbientBackground({ children, variant = "hero" }: { children?: ReactNode; variant?: "hero" | "app" }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {/* mesh */}
      <div className="absolute -top-1/3 left-1/2 -translate-x-1/2 h-[900px] w-[1400px] bg-mesh animate-mesh" />
      {/* grid */}
      <div className="absolute inset-0 bg-grid opacity-40 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_75%)]" />
      {/* orbs */}
      <div className="absolute top-40 -left-20 h-72 w-72 rounded-full blur-3xl opacity-40 animate-float" style={{background: "radial-gradient(circle, #3B82F6, transparent 70%)"}} />
      <div className="absolute bottom-20 right-0 h-96 w-96 rounded-full blur-3xl opacity-30 animate-float" style={{background: "radial-gradient(circle, #7C3AED, transparent 70%)", animationDelay: "-3s"}} />
      {variant === "hero" && (
        <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-background to-transparent" />
      )}
      {children}
    </div>
  );
}

export function Logo({ className = "", showWordmark = true, size = 36 }: { className?: string; showWordmark?: boolean; size?: number }) {
  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div
        className="relative grid place-items-center shrink-0"
        style={{
          height: size,
          width: size,
          filter: "drop-shadow(0 0 14px rgba(124,58,237,0.55)) drop-shadow(0 0 4px rgba(37,99,235,0.4))",
        }}
      >
        <img src={logoAsset.url} alt="AIBI Nexus" className="h-full w-full object-contain" />
      </div>
      {showWordmark && (
        <span className="text-[15px] font-semibold tracking-tight font-display">
          AIBI <span className="text-muted-foreground font-normal">Nexus</span>
        </span>
      )}
    </div>
  );
}
