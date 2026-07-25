import { createFileRoute } from "@tanstack/react-router";
import { AuthScreen } from "./sign-in";

export const Route = createFileRoute("/sign-up")({
  head: () => ({
    meta: [
      { title: "Create account — AIBI Nexus" },
      { name: "description", content: "Create your AIBI Nexus workspace and hire your first AI business analyst in seconds." },
      { property: "og:title", content: "Create account — AIBI Nexus" },
      { property: "og:description", content: "Create your AIBI Nexus workspace and hire your first AI business analyst." },
    ],
  }),
  component: () => <AuthScreen mode="sign-up" />,
});
