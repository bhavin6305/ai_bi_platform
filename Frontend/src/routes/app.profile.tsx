import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ArrowRight, CalendarDays, Database, Mail, Save, UserRound } from "lucide-react";
import { AibiApi, type UserProfile } from "@/lib/aibi-api";

export const Route = createFileRoute("/app/profile")({
  head: () => ({ meta: [{ title: "Profile — AIBI Platform" }] }),
  component: ProfilePage,
});

function ProfilePage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: AibiApi.profile });
  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: AibiApi.sessions });

  useEffect(() => {
    if (profileQuery.data) setName(profileQuery.data.full_name);
  }, [profileQuery.data]);

  const saveProfile = useMutation({
    mutationFn: (fullName: string) => AibiApi.updateSettings({ full_name: fullName }),
    onSuccess: async (settings) => {
      localStorage.setItem("aibi_settings", JSON.stringify(settings));
      window.dispatchEvent(new CustomEvent("aibi-settings-updated", { detail: settings }));
      await queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile name saved.");
    },
    onError: () => toast.error("Could not save your profile."),
  });

  const profile = profileQuery.data;
  if (profileQuery.isLoading) return <div className="mx-auto max-w-4xl px-6 py-16 text-sm text-white/45">Loading profile...</div>;
  if (profileQuery.isError || !profile) return (
    <div className="mx-auto max-w-3xl px-6 py-20 text-center">
      <UserRound className="mx-auto h-8 w-8 text-cyan-200/70" />
      <h1 className="mt-4 text-xl font-semibold text-white">Sign in to view your profile</h1>
      <p className="mt-2 text-sm text-white/45">Create an account or sign in to manage your profile and dataset history.</p>
      <Link to="/sign-in" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950">Sign in <ArrowRight className="h-4 w-4" /></Link>
    </div>
  );

  return <ProfileDetails profile={profile} name={name} setName={setName} datasetCount={sessionsQuery.data?.length ?? 0} saving={saveProfile.isPending} onSave={() => saveProfile.mutate(name.trim())} />;
}

function ProfileDetails({ profile, name, setName, datasetCount, saving, onSave }: { profile: UserProfile; name: string; setName: (name: string) => void; datasetCount: number; saving: boolean; onSave: () => void }) {
  const initial = profile.full_name.trim().slice(0, 1).toUpperCase() || "U";
  const joinedDate = profile.created_at ? new Date(profile.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }) : "Unavailable";

  return <div className="mx-auto max-w-5xl px-5 py-9 sm:px-8">
    <header><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-200/65">Account</p><h1 className="mt-2 text-2xl font-semibold text-white">Your profile</h1><p className="mt-1 text-sm text-white/45">Manage your account identity and find your saved analyses.</p></header>
    <div className="mt-7 grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
      <section className="rounded-xl border border-white/[0.09] bg-[#10131b]/90 p-5 sm:p-6">
        <div className="flex items-center gap-4 border-b border-white/[0.07] pb-5"><span className="grid h-14 w-14 place-items-center rounded-xl bg-gradient-to-br from-violet-400/25 to-cyan-300/15 text-xl font-semibold text-white">{initial}</span><div><h2 className="text-sm font-semibold text-white">Account details</h2><p className="mt-1 text-xs text-white/40">Your sign-in identity</p></div></div>
        <form className="mt-5 space-y-4" onSubmit={(event) => { event.preventDefault(); onSave(); }}>
          <label className="block text-xs text-white/50">Display name<input required minLength={1} maxLength={120} value={name} onChange={(event) => setName(event.target.value)} className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-200/50" /></label>
          <label className="block text-xs text-white/50">Email address<div className="mt-1.5 flex items-center gap-2 rounded-lg border border-white/[0.06] bg-black/10 px-3 py-2.5 text-sm text-white/65"><Mail className="h-4 w-4 text-white/35" />{profile.email}</div><span className="mt-1 block text-[10px] text-white/30">Email changes are not available from this profile.</span></label>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/[0.07] pt-4"><span className="flex items-center gap-2 text-xs text-white/40"><CalendarDays className="h-3.5 w-3.5" />Joined {joinedDate}</span><button disabled={saving || !name.trim() || name.trim() === profile.full_name} className="inline-flex items-center gap-2 rounded-lg bg-cyan-300 px-3.5 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"><Save className="h-3.5 w-3.5" />{saving ? "Saving..." : "Save profile"}</button></div>
        </form>
      </section>
      <aside className="space-y-3">
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><div className="flex items-center gap-2 text-xs text-white/45"><Database className="h-4 w-4 text-cyan-200" />Saved datasets</div><div className="mt-3 text-3xl font-semibold text-white">{datasetCount}</div><Link to="/app/sessions" className="mt-3 inline-flex items-center gap-1.5 text-xs text-cyan-100/75 hover:text-cyan-100">Open dataset history <ArrowRight className="h-3.5 w-3.5" /></Link></div>
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.025] p-4"><p className="text-xs font-medium text-white/75">Account ID</p><p className="mt-2 break-all font-mono text-[11px] text-white/35">{profile.user_id}</p></div>
      </aside>
    </div>
  </div>;
}
