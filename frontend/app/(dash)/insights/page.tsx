"use client";

import { Sparkles } from "lucide-react";
import { useState } from "react";
import { Badge, Button, Empty, ErrorState, LinkButton, PageHeader, PageSkeleton, SyntheticBadge, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Insight = { id: string; source: string; is_simulated: boolean; incident_id: string | null; website_id: string | null; created_at: string; content: { summary: string; likely_causes: string[]; troubleshooting_steps: string[]; preventive_actions: string[]; confidence_note: string } };
type Incident = { id: string; public_id: string; website_id: string; title: string; severity: string; is_simulated: boolean };
type Site = { id: string; name: string; url: string; latest_status: string };

export default function InsightsPage() {
  const [busy, setBusy] = useState("");
  const toast = useToast();
  const { data, error, loading, reload } = useLoad(() => Promise.all([api<Site[]>("/websites"), api<Incident[]>("/incidents"), api<Insight[]>("/insights")]).then(([sites, incidents, insights]) => ({ sites, incidents, insights })));

  async function analyze(incidentId: string) {
    setBusy(incidentId);
    try { await api(`/incidents/${incidentId}/ai`, { method: "POST" }); toast("success", "Gemini RCA explanation refreshed."); await reload(); }
    catch (e) { toast("error", e instanceof Error ? e.message : "AI analysis failed"); }
    finally { setBusy(""); }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="AI insights" description="Gemini is used only when a key is configured on the server and quota is available. Otherwise these cards are rule-based and say so." />
      {loading && !data ? <PageSkeleton rows={1} /> : error ? <ErrorState message={error} onRetry={reload} /> : !data || (data.sites.length === 0 && data.insights.length === 0 && data.incidents.length === 0) ? (
        <Empty icon={<Sparkles className="h-6 w-6" />} title="No insights yet" body="Insights are saved when an incident is created." />
      ) : (
        <div className="space-y-4">{data.sites.map((site) => {
          const incidents = data.incidents.filter((row) => row.website_id === site.id);
          const insights = data.insights.filter((row) => row.website_id === site.id);
          return <section key={site.id} className="card space-y-3"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="font-semibold text-slate-900 dark:text-white">{site.name}</h2><p className="muted break-all">{site.url}</p></div><Badge tone="slate">{site.latest_status}</Badge></div>{incidents.length === 0 ? <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">No incidents detected</p> : incidents.map((incident) => {
            const insight = insights.find((row) => row.incident_id === incident.id);
            return <article key={incident.id} className="rounded-xl border border-slate-200 p-4 dark:border-white/10"><div className="flex flex-wrap items-center gap-2"><strong>{incident.public_id}</strong><Badge tone="indigo">{insight?.source || "RCA available"}</Badge>{incident.is_simulated && <SyntheticBadge />}</div><h3 className="mt-2 font-semibold">{incident.title}</h3>{insight ? <><p className="mt-1">{insight.content.summary}</p><p className="muted mt-1">{insight.content.confidence_note}</p><span className="muted">{fmtDate(insight.created_at)}</span></> : <p className="muted mt-1">No saved AI explanation yet.</p>}<div className="mt-3 flex gap-2">{!incident.is_simulated && <Button variant="secondary" loading={busy === incident.id} onClick={() => analyze(incident.id)}><Sparkles className="h-4 w-4" /> Analyze</Button>}{incident.is_simulated && <span className="muted text-xs">Synthetic RCA is rule-based only.</span>}<LinkButton href={`/incidents/${incident.id}`} variant="secondary">View incident</LinkButton></div></article>;
          })}</section>;
        })}{data.insights.filter((row) => !row.website_id || !data.sites.some((site) => site.id === row.website_id)).map((r) => <article key={r.id} className="card space-y-2"><div className="flex flex-wrap items-center gap-2"><Badge tone="indigo">{r.source}</Badge>{r.is_simulated && <SyntheticBadge />}<span className="muted">{fmtDate(r.created_at)}</span></div><h2 className="font-semibold">{r.content.summary}</h2><p className="muted">{r.content.confidence_note}</p>{(r.content.likely_causes || []).length > 0 && <ul className="list-disc pl-5 text-sm">{r.content.likely_causes.map((c) => <li key={c}>{c}</li>)}</ul>}</article>)}</div>
      )}
    </div>
  );
}
