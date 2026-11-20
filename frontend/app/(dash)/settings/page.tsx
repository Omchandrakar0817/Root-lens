"use client";

import { Copy, KeyRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { Badge, Button, ErrorState, PageHeader, PageSkeleton, fmtDate, useLoad, useToast } from "@/components/ui";
import { api, loadSession, saveSession, type User } from "@/lib/api";

type Agent = { id: string; name: string; last_seen_at: string | null; revoked: boolean };

export default function SettingsPage() {
  const toast = useToast();
  const { data, error, loading, reload } = useLoad(async () => {
    const [user, agents] = await Promise.all([api<User>("/auth/me"), api<Agent[]>("/agents")]);
    return { user, agents };
  });
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [token, setToken] = useState("");

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const d = new FormData(event.currentTarget);
    const full_name = String(d.get("full_name") || "").trim();
    if (full_name.length < 2) return toast("error", "Enter your name.");
    setSaving(true);
    try {
      const theme = String(d.get("theme"));
      const updated = await api<User>("/auth/me", { method: "PATCH", body: JSON.stringify({ full_name, notify_email: d.get("notify_email") === "on", theme }) });
      const session = loadSession();
      if (session) saveSession({ ...session, user: updated });
      if (theme === "dark" || theme === "light") { document.documentElement.classList.toggle("dark", theme === "dark"); localStorage.setItem("theme", theme); }
      else { localStorage.removeItem("theme"); document.documentElement.classList.toggle("dark", matchMedia("(prefers-color-scheme: dark)").matches); }
      toast("success", "Profile saved.");
      await reload();
    } catch (e) { toast("error", e instanceof Error ? e.message : "Could not save profile"); } finally { setSaving(false); }
  }

  async function createAgent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setCreating(true);
    try { const c = await api<{ token: string }>("/agents", { method: "POST", body: JSON.stringify({ name: String(new FormData(form).get("name")).trim() }) }); setToken(c.token); form.reset(); await reload(); }
    catch (e) { toast("error", e instanceof Error ? e.message : "Could not create agent"); } finally { setCreating(false); }
  }
  async function revoke(id: string) {
    try { await api(`/agents/${id}/revoke`, { method: "POST" }); toast("success", "Agent revoked."); await reload(); } catch (e) { toast("error", e instanceof Error ? e.message : "Could not revoke agent"); }
  }
  async function copy() {
    try { await navigator.clipboard.writeText(token); toast("success", "Token copied."); } catch { toast("error", "Copy failed. Select the token and copy it manually."); }
  }

  if (loading && !data) return <PageSkeleton rows={1} />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={reload} />;
  const { user, agents } = data;

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" />
      <form className="card max-w-xl space-y-4" onSubmit={saveProfile}>
        <h2 className="font-semibold">Profile</h2>
        <div><label className="label" htmlFor="full_name">Name</label><input id="full_name" className="input" name="full_name" defaultValue={user.full_name} required /></div>
        <p className="muted">{user.email} · {user.role}</p>
        <label className="flex items-center gap-2 text-sm"><input name="notify_email" type="checkbox" className="h-4 w-4 accent-brand" defaultChecked={user.notify_email} /> Save my email notification preference (delivery is not active yet)</label>
        <div><label className="label" htmlFor="theme">Theme</label><select id="theme" className="input" name="theme" defaultValue={user.theme}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></div>
        <Button type="submit" loading={saving}>Save changes</Button>
      </form>
      <section className="card max-w-xl space-y-4">
        <h2 className="flex items-center gap-2 font-semibold"><KeyRound className="h-4 w-4 text-brand" /> Optional monitoring agent</h2>
        <p className="muted">Install the agent only on a machine you are allowed to monitor. URL scans never invent CPU, RAM, or disk numbers.</p>
        <form className="flex gap-2" onSubmit={createAgent}><label className="sr-only" htmlFor="agent-name">Agent name</label><input id="agent-name" className="input" name="name" placeholder="Agent name" required /><Button type="submit" loading={creating}>Create</Button></form>
        {token && <div role="status" className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-500/10 dark:text-amber-200"><p className="font-medium">Token shown once. Copy it now.</p><p className="mt-1 break-all font-mono text-xs">{token}</p><Button variant="secondary" className="mt-2" onClick={copy}><Copy className="h-4 w-4" /> Copy token</Button></div>}
        {agents.length === 0 ? <p className="muted">No agents yet.</p> : <ul className="divide-y divide-slate-200/70 text-sm dark:divide-white/10">{agents.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5"><span>{a.name} <Badge tone={a.revoked ? "red" : "green"}>{a.revoked ? "revoked" : "active"}</Badge><span className="muted block">Last seen {a.last_seen_at ? fmtDate(a.last_seen_at) : "never"}</span></span>{!a.revoked && <Button variant="secondary" onClick={() => revoke(a.id)}>Revoke</Button>}</li>))}</ul>}
      </section>
    </div>
  );
}
