"use client";

import { ArrowLeft, ScanSearch } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Button, ErrorState, PageHeader, PageSkeleton, StatusBadge, SyntheticBadge, Tabs, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { chartAxis, chartTip } from "@/lib/chart";

type Finding = { message: string; severity: string };
type Payload = {
  website: { name: string; url: string; latest_status: string };
  availability: { uptime_percent: number | null; message?: string; points: { checked_at: string; response_time_ms: number | null; http_status: number | null; is_up: boolean; error_type: string | null }[] };
  security: { message?: string; https_available?: boolean; cert_valid?: boolean | null; days_until_expiry?: number | null; findings?: Finding[] };
  seo: { message?: string; title?: string; findings?: Finding[] };
  performance: { strategy: string; available: boolean; error_message?: string; performance_score?: number; accessibility_score?: number; seo_score?: number; best_practices_score?: number; lcp_ms?: number; lcp_source?: string; inp_ms?: number; inp_source?: string; cls?: number; cls_source?: string; fcp_ms?: number; tbt_ms?: number; opportunities?: { title?: string | null; display?: string | null }[] }[];
  scans: { id: string; status: string; trigger: string; created_at: string; is_simulated: boolean }[];
  anomalies: { id: string; metric: string; record_type: string; method: string; model_trained: boolean; score: number | null; is_anomaly: boolean; value: number | null; baseline: number | null; evidence: { note?: string }; is_simulated: boolean; detected_at: string }[];
  incidents: { id: string; public_id: string; title: string; severity: string; status: string; is_simulated: boolean; detected_at: string }[];
};

const tabs = [{ id: "availability", label: "Availability" }, { id: "security", label: "Security & SEO" }, { id: "performance", label: "PageSpeed" }, { id: "anomalies", label: "Anomalies" }, { id: "incidents", label: "Incidents & scans" }];

export default function WebsiteDetailPage() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const [tab, setTab] = useState("availability");
  const [scanning, setScanning] = useState(false);
  const { data, error, loading, reload } = useLoad<Payload>(async () => {
    const [website, availability, security, performance, seo, scans, anomalies, incidents] = await Promise.all(
      ["", "/availability", "/security", "/performance", "/seo", "/scans", "/anomalies", "/incidents"].map((p) => api(`/websites/${id}${p}`))
    );
    return { website, availability, security, performance, seo, scans, anomalies, incidents } as Payload;
  }, [id]);

  async function scan() {
    setScanning(true);
    try { const r = await api<{ detail: string; execution: string }>(`/websites/${id}/scans`, { method: "POST" }); toast("success", `${r.detail} (${r.execution}).`); await reload(); }
    catch (e) { toast("error", e instanceof Error ? e.message : "Scan failed"); } finally { setScanning(false); }
  }

  if (loading && !data) return <PageSkeleton rows={2} />;
  if (error || !data) return <ErrorState message={error || "Not found"} onRetry={reload} />;
  const { website, availability, security, seo, performance, scans, anomalies, incidents } = data;
  const chart = [...(availability.points || [])].reverse().filter((p) => p.response_time_ms != null).map((p) => ({ time: new Date(p.checked_at).toLocaleString(), ms: p.response_time_ms, anomaly: null as number | null }));
  const chronologicalPoints = [...(availability.points || [])].reverse().filter((point) => point.response_time_ms != null);
  for (const anomaly of anomalies.filter((item) => !item.is_simulated && item.record_type === "anomaly" && item.metric === "response_time_ms" && item.value != null)) {
    const anomalyTime = new Date(anomaly.detected_at).getTime();
    let nearest = 0;
    let nearestDistance = Number.POSITIVE_INFINITY;
    chronologicalPoints.forEach((point, index) => {
      const distance = Math.abs(new Date(point.checked_at).getTime() - anomalyTime);
      if (distance < nearestDistance) {
        nearest = index;
        nearestDistance = distance;
      }
    });
    if (chart.length > 0) chart[nearest].anomaly = anomaly.value;
  }
  const findings = (list?: Finding[]) => (list || []).length === 0 ? <p className="muted mt-3">No findings.</p> : <ul className="mt-3 space-y-2 text-sm">{list!.map((f) => <li key={f.message} className="flex gap-2"><StatusBadge status={f.severity} /><span>{f.message}</span></li>)}</ul>;

  return (
    <div className="space-y-6">
      <Link href="/websites" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 no-underline hover:text-brand dark:text-slate-400"><ArrowLeft className="h-4 w-4" /> All websites</Link>
      <PageHeader title={website.name} description={<span className="break-all">{website.url}</span>} actions={<><StatusBadge status={website.latest_status} /><Button loading={scanning} onClick={scan}><ScanSearch className="h-4 w-4" /> Scan now</Button></>} />
      <Tabs tabs={tabs} value={tab} onChange={setTab} />
      <div key={tab} className="animate-pop space-y-4">
        {tab === "availability" && (
          <section className="card">
            <h2 className="font-semibold">Availability{availability.uptime_percent != null ? ` · ${availability.uptime_percent}% of stored checks` : ""}</h2>
            {availability.message && <p className="muted mt-2">{availability.message}</p>}
            {chart.length >= 2 ? <div className="mt-4 h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.2} vertical={false} /><XAxis dataKey="time" hide /><YAxis unit=" ms" width={64} {...chartAxis} /><Tooltip {...chartTip} /><Line dataKey="ms" name="Response history" stroke="#4F46E5" strokeWidth={2} dot={false} animationDuration={700} /><Line type="monotone" dataKey="anomaly" name="Anomaly" stroke="none" dot={{ r: 4, fill: "#fb923c", strokeWidth: 0 }} connectNulls={false} /></LineChart></ResponsiveContainer></div> : <p className="muted mt-3">Response history appears after at least 2 real measurements.</p>}
            <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead className="muted"><tr><th className="py-2 pr-4 font-medium">Checked</th><th className="pr-4 font-medium">Result</th><th className="pr-4 font-medium">HTTP</th><th className="pr-4 font-medium">Time</th><th className="font-medium">Error</th></tr></thead>
              <tbody className="divide-y divide-slate-200/70 dark:divide-white/10">{(availability.points || []).slice(0, 8).map((p, i) => <tr key={p.checked_at + i}><td className="whitespace-nowrap py-2 pr-4">{fmtDate(p.checked_at)}</td><td className="pr-4"><Badge tone={p.is_up ? "green" : "red"}>{p.is_up ? "up" : "not up"}</Badge></td><td className="pr-4">{p.http_status ?? "—"}</td><td className="pr-4">{p.response_time_ms ?? "—"} ms</td><td>{p.error_type || "ok"}</td></tr>)}</tbody></table></div>
          </section>
        )}
        {tab === "security" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="card"><h2 className="font-semibold">Security configuration</h2>{security.message ? <p className="muted mt-2">{security.message}</p> : <><p className="muted mt-2">HTTPS: {String(security.https_available)} · certificate valid: {String(security.cert_valid)} · days to expiry: {security.days_until_expiry ?? "unknown"}</p>{findings(security.findings)}</>}</section>
            <section className="card"><h2 className="font-semibold">SEO and accessibility</h2>{seo.message ? <p className="muted mt-2">{seo.message}</p> : <p className="muted mt-2">Title: {seo.title || "missing"}</p>}{findings(seo.findings)}</section>
          </div>
        )}
        {tab === "performance" && (
          <section className="card"><h2 className="font-semibold">PageSpeed</h2>
            {performance.length === 0 ? <p className="muted mt-2">No PageSpeed results yet. They need a PageSpeed API key configured on the server.</p> : (
              <div className="mt-3 grid gap-3 md:grid-cols-2">{performance.map((row, i) => (
                <article key={row.strategy + i} className="rounded-xl border border-slate-200 p-4 dark:border-white/10">
                  <h3 className="font-medium capitalize">{row.strategy}</h3>
                  {!row.available ? <p className="muted mt-2">{row.error_message}</p> : <>
                    <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">{[["Performance", row.performance_score], ["Accessibility", row.accessibility_score], ["SEO", row.seo_score], ["Best practices", row.best_practices_score]].map(([k, v]) => <div key={String(k)} className="rounded-lg bg-slate-50 p-2 dark:bg-white/5"><dt className="muted">{k}</dt><dd className="font-display text-xl font-bold">{v ?? "—"}</dd></div>)}</dl>
                    <p className="muted mt-3">LCP {row.lcp_ms ?? "missing"} ({row.lcp_source || "n/a"}) · CLS {row.cls ?? "missing"} ({row.cls_source || "n/a"}) · INP {row.inp_ms ?? "missing"} ({row.inp_source || "not returned"}) · FCP {row.fcp_ms ?? "missing"} · TBT {row.tbt_ms ?? "missing"}</p>
                    <div className="mt-3">
                      <h4 className="text-sm font-semibold">Recommendations</h4>
                      {(row.opportunities ?? []).length === 0 ? <p className="muted mt-1 text-sm">No recommendations returned for this run.</p> : (
                        <ul className="mt-1 space-y-1 text-sm">{row.opportunities!.map((item, index) => <li key={`${item.title ?? "recommendation"}-${index}`}><span className="font-medium">{item.title || "PageSpeed opportunity"}</span>{item.display && <span className="muted"> · {item.display}</span>}</li>)}</ul>
                      )}
                    </div></>}
                </article>))}</div>)}
          </section>
        )}
        {tab === "anomalies" && (
          <section className="card"><h2 className="font-semibold">Anomaly detection</h2>
            {anomalies.length === 0 ? <p className="muted mt-2">No anomaly records yet. Run several scans to build a baseline.</p> : (
              <ul className="mt-3 space-y-2 text-sm">{anomalies.slice(0, 10).map((a) => (
                <li key={a.id} className={`rounded-xl border p-3 ${a.is_anomaly ? "border-orange-300 bg-orange-50 dark:border-orange-500/40 dark:bg-orange-500/10" : "border-slate-200 dark:border-white/10"}`}>
                  <div className="flex flex-wrap items-center gap-2"><span className="font-medium">{a.metric}</span><Badge tone="slate">{a.method}</Badge><Badge tone={a.model_trained ? "indigo" : "slate"}>{a.model_trained ? "model trained" : "no model yet"}</Badge>{a.is_anomaly ? <Badge tone="orange">Anomaly</Badge> : <Badge tone="green">Normal</Badge>}{a.is_simulated && <SyntheticBadge />}</div>
                  <p className="muted mt-1">value {a.value ?? "—"} · baseline {a.baseline ?? "—"} · score {a.score ?? "—"}</p>{a.evidence?.note && <p className="muted">{a.evidence.note}</p>}
                </li>))}</ul>)}
          </section>
        )}
        {tab === "incidents" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="card"><h2 className="font-semibold">Incidents for this website</h2>
              {incidents.length === 0 ? <p className="muted mt-2">No incidents recorded.</p> : <ul className="mt-3 divide-y divide-slate-200/70 text-sm dark:divide-white/10">{incidents.map((i) => <li key={i.id} className="py-2.5"><Link href={`/incidents/${i.id}`} className="font-semibold text-brand">{i.public_id}</Link> · {i.title}<div className="mt-1 flex flex-wrap items-center gap-2"><StatusBadge status={i.severity} /><StatusBadge status={i.status} />{i.is_simulated && <SyntheticBadge />}<span className="muted">{fmtDate(i.detected_at)}</span></div></li>)}</ul>}
            </section>
            <section className="card"><h2 className="font-semibold">Scan history</h2>
              {scans.length === 0 ? <p className="muted mt-2">No scans stored.</p> : <ul className="mt-3 divide-y divide-slate-200/70 text-sm dark:divide-white/10">{scans.map((s) => <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5"><span>{fmtDate(s.created_at)} · {s.trigger}</span><span className="flex gap-2"><StatusBadge status={s.status} />{s.is_simulated && <SyntheticBadge />}</span></li>)}</ul>}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
