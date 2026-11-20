"use client";

import { ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Empty, ErrorState, PageHeader, PageSkeleton, StatusBadge, SyntheticBadge, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Incident = { id: string; public_id: string; website_id: string; title: string; severity: string; status: string; category: string; is_simulated: boolean; detected_at: string; symptoms?: string[] };
type Site = { id: string; name: string; url: string; latest_status: string };

export default function IncidentsPage() {
  const initial = typeof window === "undefined" ? new URLSearchParams() : new URLSearchParams(window.location.search);
  const [severity, setSeverity] = useState(initial.get("severity") || "");
  const [status, setStatus] = useState(initial.get("status") || "");
  const [simulated, setSimulated] = useState(initial.get("simulated") || "");
  const [busy, setBusy] = useState("");
  const toast = useToast();
  const { data, error, loading, reload } = useLoad(async () => {
    const params = new URLSearchParams();
    if (severity) params.set("severity", severity);
    if (status) params.set("status", status);
    if (simulated !== "") params.set("simulated", simulated);
    const qs = params.toString();
    const [sites, rows] = await Promise.all([api<Site[]>("/websites"), api<Incident[]>(`/incidents${qs ? `?${qs}` : ""}`)]);
    return { sites, rows };
  }, [severity, status, simulated]);

  async function analyze(row: Incident) {
    setBusy(row.id);
    try { await api(`/incidents/${row.id}/ai`, { method: "POST" }); toast("success", "Gemini RCA explanation refreshed."); await reload(); }
    catch (e) { toast("error", e instanceof Error ? e.message : "AI analysis failed"); }
    finally { setBusy(""); }
  }

  const select = (label: string, value: string, set: (v: string) => void, options: [string, string][]) => (
    <div><label className="sr-only">{label}</label><select aria-label={label} className="input !w-auto" value={value} onChange={(e) => set(e.target.value)}>{options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
  );

  return (
    <div className="space-y-6">
      <PageHeader title="Incidents" actions={<>
        {select("Severity", severity, setSeverity, [["", "All severities"], ...["critical", "high", "medium", "low"].map((s) => [s, s] as [string, string])])}
        {select("Status", status, setStatus, [["", "All statuses"], ...["open", "acknowledged", "resolved"].map((s) => [s, s] as [string, string])])}
        {select("Type", simulated, setSimulated, [["", "All types"], ["false", "Live only"], ["true", "Synthetic only"]])}
      </>} />
      {loading && !data ? <PageSkeleton rows={1} /> : error ? <ErrorState message={error} onRetry={reload} /> : !data || (data.sites.length === 0 && data.rows.length === 0) ? (
        <Empty icon={<ShieldCheck className="h-6 w-6" />} title="No incidents" body="Incidents are created after a meaningful, confirmed problem. One transient timeout is recorded but does not open an incident." />
      ) : (
        <div className="space-y-4">
          {data.sites.map((site) => {
            const rows = data.rows.filter((row) => row.website_id === site.id);
            return (
              <section key={site.id} className="card space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold text-slate-900 dark:text-white">{site.name}</h2><p className="muted break-all">{site.url}</p></div><StatusBadge status={site.latest_status} /></div>
                {rows.length === 0 ? <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">No incidents detected</p> : rows.map((row) => (
                  <div key={row.id} className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-200 p-3 dark:border-white/10">
                    <Link href={`/incidents/${row.id}`} className="min-w-0 flex-1 no-underline"><div className="flex flex-wrap items-center gap-2"><strong>{row.public_id}</strong><StatusBadge status={row.severity} /><StatusBadge status={row.status} />{row.is_simulated && <SyntheticBadge />}</div><p className="mt-1 font-medium text-slate-900 dark:text-white">{row.title}</p><p className="muted">{row.symptoms?.length ? row.symptoms.join(" · ") : "No additional error detail recorded."}</p><p className="muted">{row.category} · {fmtDate(row.detected_at)}</p></Link>
                    {!row.is_simulated && <Button variant="secondary" loading={busy === row.id} onClick={() => analyze(row)}><Sparkles className="h-4 w-4" /> Analyze</Button>}
                  </div>
                ))}
              </section>
            );
          })}
          {data.rows.filter((row) => row.is_simulated && !data.sites.some((site) => site.id === row.website_id)).map((row) => (
            <section key={row.id} className="card"><div className="flex flex-wrap items-center gap-2"><strong>{row.public_id}</strong><StatusBadge status={row.severity} /><StatusBadge status={row.status} /><SyntheticBadge /></div><p className="mt-1 font-medium">{row.title}</p><div className="mt-3 flex gap-2"><Link href={`/incidents/${row.id}`} className="btn-secondary">View incident</Link><span className="muted text-sm">Synthetic RCA is rule-based only.</span></div></section>
          ))}
        </div>
      )}
    </div>
  );
}
