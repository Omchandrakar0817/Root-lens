"use client";

import { Globe, Play, Pause, ScanSearch, Square, Trash2 } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { Badge, Button, ConfirmDialog, Empty, ErrorState, LinkButton, PageHeader, PageSkeleton, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Site = { id: string; name: string; url: string; monitoring_state: string; latest_status: string; latest_checked_at: string | null; interval_seconds: number | null };
type SiteMetrics = {
  availability: { points: { http_status: number | null; response_time_ms: number | null }[] };
  security: { message?: string; https_available?: boolean; cert_valid?: boolean | null };
  performance: { strategy: string; available: boolean; performance_score: number | null }[];
};
const intervals = [[300, "5 min"], [900, "15 min"], [1800, "30 min"], [3600, "1 hour"]] as const;

function statusDisplay(status: string) {
  switch (status.toLowerCase()) {
    case "healthy": return { label: "Healthy", tone: "green" as const };
    case "degraded": return { label: "Degraded", tone: "amber" as const };
    case "down": return { label: "Down", tone: "red" as const };
    default: return { label: "Unknown", tone: "slate" as const };
  }
}

function WebsiteStatus({ status }: { status: string }) {
  const display = statusDisplay(status);
  return <Badge tone={display.tone}>{display.label}</Badge>;
}

function Metric({ label, value, valueClassName = "" }: { label: string; value: string; valueClassName?: string }) {
  return (
    <div className="min-w-0 rounded-lg bg-slate-50 p-2 dark:bg-white/5">
      <dt className="muted text-xs">{label}</dt>
      <dd className={`mt-1 truncate text-sm font-semibold ${valueClassName}`}>{value}</dd>
    </div>
  );
}

function WebsiteMetrics({ site }: { site: Site }) {
  const { data, error, loading } = useLoad(async () => {
    const [availability, security, performance] = await Promise.all([
      api<SiteMetrics["availability"]>(`/websites/${site.id}/availability`),
      api<SiteMetrics["security"]>(`/websites/${site.id}/security`),
      api<SiteMetrics["performance"]>(`/websites/${site.id}/performance`),
    ]);
    return { availability, security, performance };
  }, [site.id, site.latest_checked_at]);

  if (loading && !data) return <p className="muted mt-4 text-sm">Loading scan metrics…</p>;

  const latest = data?.availability.points[0];
  const security = data?.security;
  const score = data?.performance.find((row) => row.available && row.performance_score !== null);
  const sslStatus = security?.message
    ? "Not checked"
    : security?.cert_valid === true
      ? "Valid"
      : security?.cert_valid === false
        ? "Invalid"
        : security?.https_available === false
          ? "N/A"
          : "Not checked";
  const sslColor = sslStatus === "Valid" ? "text-emerald-700 dark:text-emerald-300" : sslStatus === "Invalid" ? "text-red-700 dark:text-red-300" : "text-slate-500 dark:text-slate-400";

  return (
    <div className="mt-4">
      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <Metric label="HTTP status" value={latest?.http_status == null ? "N/A" : String(latest.http_status)} />
        <Metric label="Response time" value={latest?.response_time_ms == null ? "N/A" : `${Math.round(latest.response_time_ms)} ms`} />
        <Metric label="SSL certificate" value={sslStatus} valueClassName={sslColor} />
        <Metric label="PageSpeed" value={score?.performance_score == null ? "N/A" : `${score.performance_score} / 100 · ${score.strategy}`} />
        <Metric label="Last scan" value={site.latest_checked_at ? fmtDate(site.latest_checked_at) : "Not checked"} />
      </dl>
      {error && <p role="alert" className="mt-2 text-xs text-red-700 dark:text-red-300">Monitoring metrics could not be loaded: {error}</p>}
    </div>
  );
}

export default function WebsitesPage() {
  const toast = useToast();
  const { data: sites, error, loading, reload } = useLoad(() => api<Site[]>("/websites"));
  const [adding, setAdding] = useState(false);
  const [busy, setBusy] = useState("");
  const [toDelete, setToDelete] = useState<Site | null>(null);
  const [every, setEvery] = useState<Record<string, number>>({});

  async function addSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setAdding(true);
    try {
      await api("/websites", { method: "POST", body: JSON.stringify({ name: String(data.get("name")).trim(), url: String(data.get("url")).trim() }) });
      form.reset();
      toast("success", "Website added.");
      await reload();
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Could not add website");
    } finally {
      setAdding(false);
    }
  }

  async function run(key: string, task: () => Promise<string>) {
    setBusy(key);
    try { toast("success", await task()); await reload(); } catch (err) { toast("error", err instanceof Error ? err.message : "Request failed"); } finally { setBusy(""); }
  }

  const monitor = (site: Site, state: "active" | "paused" | "stopped") =>
    run(`${site.id}:${state}`, async () => {
      await api(`/websites/${site.id}/monitoring`, { method: "POST", body: JSON.stringify({ state, interval_seconds: every[site.id] || site.interval_seconds || 900 }) });
      return state === "active" ? "Monitoring is active. Scheduled runs need Redis and a worker." : `Monitoring ${state}.`;
    });
  const scan = (site: Site) => run(`${site.id}:scan`, async () => {
    const r = await api<{ detail: string; execution: string }>(`/websites/${site.id}/scans`, { method: "POST" });
    if (r.execution === "queued") {
      window.setTimeout(() => void reload(), 3000);
      window.setTimeout(() => void reload(), 10000);
    }
    return `${r.detail} (${r.execution}).`;
  });
  const remove = async () => {
    if (!toDelete) return;
    const site = toDelete;
    await run(`${site.id}:delete`, async () => { await api(`/websites/${site.id}`, { method: "DELETE" }); return `“${site.name}” deleted.`; });
    setToDelete(null);
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Websites" description="Add a public HTTP or HTTPS URL. Private, loopback and metadata addresses are rejected." />
      <form className="card grid gap-3 md:grid-cols-[1fr_1.4fr_auto] md:items-end" onSubmit={addSite}>
        <div><label className="label" htmlFor="name">Display name</label><input id="name" className="input" name="name" placeholder="Company site" required maxLength={80} /></div>
        <div><label className="label" htmlFor="url">URL</label><input id="url" className="input" name="url" type="url" placeholder="https://example.com" required /></div>
        <Button type="submit" loading={adding}>Add website</Button>
      </form>
      {loading && !sites ? <PageSkeleton rows={1} /> : error ? <ErrorState message={error} onRetry={reload} /> : !sites || sites.length === 0 ? (
        <Empty icon={<Globe className="h-6 w-6" />} title="No websites yet" body="Add your first website above to start monitoring." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {sites.map((site) => (
            <article key={site.id} className="card card-hover">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0"><Link className="text-lg font-semibold text-slate-900 hover:text-brand dark:text-white" href={`/websites/${site.id}`}>{site.name}</Link><p className="muted break-all">{site.url}</p></div>
                <WebsiteStatus status={site.latest_status} />
              </div>
              <p className="muted mt-3">Monitoring: <strong>{site.monitoring_state}</strong> · every {site.interval_seconds || "—"}s</p>
              <WebsiteMetrics site={site} />
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <Button loading={busy === `${site.id}:scan`} onClick={() => scan(site)}><ScanSearch className="h-4 w-4" /> Scan now</Button>
                <label className="sr-only" htmlFor={`int-${site.id}`}>Check interval</label>
                <select id={`int-${site.id}`} className="input !w-auto !py-2" value={every[site.id] || site.interval_seconds || 900} onChange={(e) => setEvery({ ...every, [site.id]: Number(e.target.value) })}>
                  {intervals.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
                <Button variant="secondary" loading={busy === `${site.id}:active`} onClick={() => monitor(site, "active")}><Play className="h-4 w-4" /> Start</Button>
                <Button variant="secondary" loading={busy === `${site.id}:paused`} onClick={() => monitor(site, "paused")}><Pause className="h-4 w-4" /> Pause</Button>
                <Button variant="secondary" loading={busy === `${site.id}:stopped`} onClick={() => monitor(site, "stopped")}><Square className="h-4 w-4" /> Stop</Button>
                <Button variant="danger" onClick={() => setToDelete(site)} aria-label={`Delete ${site.name}`}><Trash2 className="h-4 w-4" /> Delete</Button>
                <LinkButton variant="secondary" href={`/websites/${site.id}`}>View details</LinkButton>
              </div>
            </article>
          ))}
        </div>
      )}
      <ConfirmDialog open={!!toDelete} title="Delete website?" body={toDelete ? `“${toDelete.name}” and all of its history will be removed permanently.` : ""} confirmLabel="Delete" loading={!!toDelete && busy === `${toDelete.id}:delete`} onConfirm={remove} onCancel={() => setToDelete(null)} />
    </div>
  );
}
