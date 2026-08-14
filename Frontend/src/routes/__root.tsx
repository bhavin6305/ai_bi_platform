import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import { Toaster } from "sonner";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import {
  CinematicLoader,
  PageTransition,
  ScrollProgress,
} from "@/components/aibi/motion";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-6 h-16 w-16 rounded-2xl glass grid place-items-center text-2xl font-semibold text-gradient-primary">404</div>
        <h1 className="text-3xl font-semibold tracking-tight">Lost in the neural mesh</h1>
        <p className="mt-3 text-sm text-muted-foreground">This route hasn't been trained yet.</p>
        <div className="mt-8">
          <Link to="/" className="inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium text-white ring-glow" style={{background: "var(--gradient-primary)"}}>
            Return home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => { reportLovableError(error, { boundary: "tanstack_root_error_component" }); }, [error]);
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center glass rounded-3xl p-10">
        <h1 className="text-xl font-semibold">Something misfired</h1>
        <p className="mt-2 text-sm text-muted-foreground">A signal was lost in the pipeline.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button onClick={() => { router.invalidate(); reset(); }} className="rounded-full px-4 py-2 text-sm font-medium text-white" style={{background: "var(--gradient-primary)"}}>Try again</button>
          <a href="/" className="rounded-full border border-white/10 px-4 py-2 text-sm">Home</a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "AIBI Nexus — Hire an AI Business Analyst" },
      { name: "description", content: "Upload data. Get forecasts, dashboards, anomaly detection, and answers in plain English. The AI-native business intelligence platform." },
      { property: "og:title", content: "AIBI Nexus — Hire an AI Business Analyst" },
      { property: "og:description", content: "Upload data. Get forecasts, dashboards, anomaly detection, and answers in plain English. The AI-native business intelligence platform." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "AIBI Nexus — Hire an AI Business Analyst" },
      { name: "twitter:description", content: "Upload data. Get forecasts, dashboards, anomaly detection, and answers in plain English. The AI-native business intelligence platform." },
    ],
    links: [
      { rel: "icon", type: "image/png", href: "/LOGO.png" },
      { rel: "shortcut icon", type: "image/png", href: "/LOGO.png" },
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head><HeadContent /></head>
      <body className="bg-background text-foreground antialiased">
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  return (
    <QueryClientProvider client={queryClient}>
      <CinematicLoader />
      <ScrollProgress />
      <PageTransition>
        <Outlet />
      </PageTransition>
      <Toaster theme="dark" position="bottom-right" toastOptions={{ style: { background: "rgba(13,13,24,0.95)", border: "1px solid rgba(255,255,255,0.08)", color: "#f1f5f9" } }} />
    </QueryClientProvider>
  );
}
