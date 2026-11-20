"use client";

import { Sparkles, Stethoscope } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, Empty, ErrorState, LinkButton, PageHeader, PageSkeleton, StatusBadge, SyntheticBadge, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Incident = { id: string; public_id: string; website_id: string; title: string; severity: string; status: string; is_simulated: boolean };
type Site = { id: string; name: string; url: string; latest_status: string };
type Detail = { symptoms: string[]; evidence: Record<string, unknown>; rca: null | { observed_problem: string; hypotheses: { title: string; explanation: string; confidence: string; status: string; evidence: string[] }[]; recommended_actions: string[]; preventive_measures: string[] }; ai: null | { source: string; content: { likely_causes: string[]; troubleshooting_steps: string[]; preventive_actions: string[] } } };

export default function RcaPage() {
  const [busy, setBusy] = useState("");
  const toast = useToast();
  const { data, error, loading, reload } = useLoad(async () => {
    const [sites, rows] = await Promise.all([api<Site[]>("/websites"), api<Incident[]>("/incidents")]);
    const details = await Promise.all(rows.map((row) => api<Detail>(`/incidents/${row.id}`).catch(() => null)));
    return { sites, rows: rows.map((row, index) => ({ ...row, detail: details[index] })) };
  });

  async function analyze(row: Incident) {
    setBusy(row.id);
    try { await api(`/incidents/${row.id}/ai`, { method: "POST" }); toast("success", "Gemini RCA explanation refreshed."); await reload(); }
    catch (e) { toast("error", e instanceof Error ? e.message : "AI analysis failed"); }
    finally { setBusy(""); }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Root cause analysis" description="Each incident stores ranked explanations. A cause is marked confirmed only when a measurement directly shows it, such as repeated DNS failure. Everything else stays a hypothesis." />
      {loading && !data ? <PageSkeleton rows={1} /> : error ? <ErrorState message={error} onRetry={reload} /> : !data || (data.sites.length === 0 && data.rows.length === 0) ? (
        <Empty icon={<Stethoscope className="h-6 w-6" />} title="No analyses yet" body="Run a scan that confirms a problem, or open the simulator to see a labeled synthetic analysis." action={<LinkButton href="/simulator" variant="secondary">Open simulator</LinkButton>} />
      ) : (
        <div className="space-y-4">{data.sites.map((site) => {
          const rows = data.rows.filter((row) => row.website_id === site.id && (row.is_simulated || row.status === "open" || row.status === "acknowledged"));
          return <section key={site.id} className="card space-y-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold text-slate-900 dark:text-white">{site.name}</h2><p className="muted break-all">{site.url}</p></div><StatusBadge status={site.latest_status} /></div>{rows.length === 0 ? <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">No active incident requiring analysis</p> : <div className="grid gap-3 md:grid-cols-2">{rows.map((r) => { const hypotheses = r.detail?.rca?.hypotheses || []; const causes = r.detail?.ai?.content.likely_causes || hypotheses.map((h) => h.title); return <article key={r.id} className="rounded-xl border border-slate-200 p-4 dark:border-white/10"><div className="flex items-center justify-between gap-2"><strong>{r.public_id}</strong><span className="flex gap-2"><StatusBadge status={r.severity} />{r.is_simulated && <SyntheticBadge />}</span></div><p className="mt-2 font-medium">{r.detail?.rca?.observed_problem || r.title}</p>{r.detail?.symptoms?.length ? <p className="muted mt-1 text-sm">Evidence: {r.detail.symptoms.join(" · ")}</p> : null}{causes.length > 0 && <p className="muted mt-1 text-sm">Likely causes: {causes.join(" · ")}</p>}{hypotheses.length > 0 && <p className="muted mt-1 text-sm">Confidence: {hypotheses.map((h) => `${h.title} (${h.confidence})`).join(" · ")}</p>}<div className="mt-3 flex gap-2"><LinkButton href={`/incidents/${r.id}`} variant="secondary">View RCA</LinkButton>{!r.is_simulated && <Button variant="secondary" loading={busy === r.id} onClick={() => analyze(r)}><Sparkles className="h-4 w-4" /> Analyze</Button>}{r.is_simulated && <span className="muted text-xs">Rule-based synthetic RCA</span>}</div></article>; })}</div>}</section>;
        })}{data.rows.filter((row) => row.is_simulated && !data.sites.some((site) => site.id === row.website_id)).map((r) => <section key={r.id} className="card"><div className="flex items-center justify-between gap-2"><strong>{r.public_id}</strong><span className="flex gap-2"><StatusBadge status={r.severity} /><SyntheticBadge /></span></div><p className="mt-1">{r.title}</p><div className="mt-3 flex gap-2"><LinkButton href={`/incidents/${r.id}`} variant="secondary">View RCA</LinkButton><span className="muted text-sm">Rule-based synthetic RCA</span></div></section>)}</div>
      )}
    </div>
  );
}
