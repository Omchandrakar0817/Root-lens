"use client";

import Link from "next/link";
import { useState } from "react";
import { Badge, Button, ErrorState, PageSkeleton, StatusBadge, SyntheticBadge, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Website = { id: string; name: string; url: string; latest_status: string; latest_checked_at: string | null };
type Incident = {
  id: string;
  website_id: string;
  public_id: string;
  title: string;
  severity: string;
  status: string;
  is_simulated: boolean;
  detected_at: string;
  symptoms: string[];
};
type InsightContent = {
  summary?: string;
  likely_causes?: string[];
  troubleshooting_steps?: string[];
  preventive_actions?: string[];
  confidence_note?: string;
};
type Insight = { incident_id: string | null; source: string; is_simulated: boolean; content: InsightContent };
type Analysis = { source: string; content: InsightContent; is_simulated?: boolean };
type OverviewData = { websites: Website[]; incidents: Incident[]; insights: Insight[] };

function sourceLabel(source: string) {
  if (source === "gemini") return "Gemini-generated";
  if (source === "rule_based") return "Rule-based fallback";
  return source;
}

function ActionList({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return <div className="mt-2"><h4 className="text-xs font-semibold">{title}</h4><ol className="muted mt-1 list-decimal space-y-1 pl-5 text-xs">{items.map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ol></div>;
}

export function WebsiteIncidentOverview() {
  const toast = useToast();
  const [busy, setBusy] = useState("");
  const [fresh, setFresh] = useState<Record<string, Analysis>>({});
  const { data, error, loading, reload } = useLoad(async () => {
    const [websites, incidents, insights] = await Promise.all([
      api<Website[]>("/websites"),
      api<Incident[]>("/incidents"),
      api<Insight[]>("/insights"),
    ]);
    return { websites, incidents, insights };
  });

  async function analyze(incident: Incident) {
    setBusy(incident.id);
    try {
      const result = await api<Analysis>(`/incidents/${incident.id}/ai`, { method: "POST" });
      setFresh((current) => ({ ...current, [incident.id]: result }));
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Could not analyze incident");
    } finally {
      setBusy("");
    }
  }

  if (loading && !data) return <PageSkeleton rows={1} />;
  if (error || !data) return <ErrorState message={error || "Website incident data is unavailable"} onRetry={reload} />;

  const incidentsByWebsite = new Map<string, Incident[]>();
  for (const incident of data.incidents) {
    if (incident.is_simulated) continue;
    const group = incidentsByWebsite.get(incident.website_id) || [];
    group.push(incident);
    incidentsByWebsite.set(incident.website_id, group);
  }
  const savedInsights = new Map<string, Insight>();
  for (const insight of data.insights) {
    if (insight.incident_id && !savedInsights.has(insight.incident_id)) savedInsights.set(insight.incident_id, insight);
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div><h2 className="text-xl font-semibold">Website incident overview</h2><p className="muted text-sm">Live monitoring status and incident analysis for every monitored website.</p></div>
        <Link href="/incidents?simulated=false" className="text-sm font-semibold text-brand">Live incident history</Link>
      </div>
      {data.websites.length === 0 ? <p className="card muted text-sm">No monitored websites yet.</p> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {data.websites.map((website) => {
            const incidents = incidentsByWebsite.get(website.id) || [];
            return (
              <article key={website.id} className="card space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link href={`/websites/${website.id}`} className="font-semibold text-slate-900 hover:text-brand dark:text-white">{website.name}</Link>
                    <p className="muted break-all text-xs">{website.url}</p>
                  </div>
                  <StatusBadge status={website.latest_status} />
                </div>
                <p className="muted text-xs">Last scan: {website.latest_checked_at ? fmtDate(website.latest_checked_at) : "Not checked"}</p>
                {incidents.length === 0 ? (
                  <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300">No incidents detected</p>
                ) : incidents.map((incident) => {
                  const saved = fresh[incident.id] || savedInsights.get(incident.id);
                  return (
                    <div key={incident.id} className="rounded-xl border border-slate-200 p-3 dark:border-white/10">
                      <div className="flex flex-wrap items-center gap-2"><Badge tone="slate">{incident.public_id}</Badge><StatusBadge status={incident.severity} /><StatusBadge status={incident.status} />{incident.is_simulated && <SyntheticBadge />}</div>
                      <p className="mt-2 text-sm font-semibold">{incident.title}</p>
                      <p className="muted mt-1 text-sm">{incident.symptoms?.length ? incident.symptoms.join(" · ") : "No additional error detail recorded."}</p>
                      <p className="muted mt-1 text-xs">{fmtDate(incident.detected_at)}</p>
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <Link href={`/incidents/${incident.id}`} className="text-sm font-semibold text-brand">View RCA</Link>
                        {!incident.is_simulated && <Button variant="secondary" loading={busy === incident.id} onClick={() => analyze(incident)}>Analyze</Button>}
                        {incident.is_simulated && <span className="muted text-xs">Rule-based only; Gemini is bypassed for simulations.</span>}
                      </div>
                      {saved && (
                        <div className="mt-3 border-t border-slate-200 pt-3 text-sm dark:border-white/10">
                          <div className="flex flex-wrap items-center gap-2"><Badge tone={saved.source === "gemini" ? "indigo" : "slate"}>{sourceLabel(saved.source)}</Badge>{saved.is_simulated && <SyntheticBadge />}</div>
                          {saved.content.summary && <p className="mt-2">{saved.content.summary}</p>}
                          {saved.content.confidence_note && <p className="muted mt-1 text-xs">{saved.content.confidence_note}</p>}
                          <ActionList title="Likely causes" items={saved.content.likely_causes} />
                          <ActionList title="Recommended troubleshooting" items={saved.content.troubleshooting_steps} />
                          <ActionList title="Preventive actions" items={saved.content.preventive_actions} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </article>
            );
          })}
        </div>
      )}
      {data.incidents.some((incident) => incident.is_simulated) && <p className="muted text-xs">Synthetic incidents are kept separate from monitored websites. <Link href="/incidents?simulated=true" className="font-semibold text-brand">View synthetic incidents</Link></p>}
    </section>
  );
}
