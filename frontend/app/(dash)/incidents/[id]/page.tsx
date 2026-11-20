"use client";

import { ArrowLeft, CheckCheck, RotateCcw, Sparkles, Eye } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge, Button, ErrorState, PageHeader, PageSkeleton, StatusBadge, SyntheticBadge, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Detail = {
  public_id: string; title: string; severity: string; status: string; category: string; is_simulated: boolean; symptoms: string[]; evidence: Record<string, unknown>;
  timeline: { event_type: string; message: string; created_at: string; actor: string }[];
  rca: null | { observed_problem: string; hypotheses: { title: string; explanation: string; confidence: string; status: string; evidence: string[] }[]; verification_steps: string[]; recommended_actions: string[]; preventive_measures: string[] };
  ai: null | { source: string; content: { summary: string; likely_causes: string[]; troubleshooting_steps: string[]; preventive_actions: string[]; confidence_note: string } };
};
type Action = "acknowledge" | "resolve" | "reopen" | "ai";
const done: Record<Action, string> = { acknowledge: "Incident acknowledged.", resolve: "Incident resolved.", reopen: "Incident reopened.", ai: "AI note refreshed." };

const List = ({ title, items }: { title: string; items?: string[] }) => !items || items.length === 0 ? null : (
  <div><h3 className="mt-4 text-sm font-semibold">{title}</h3><ul className="muted mt-1 list-disc space-y-1 pl-5">{items.map((i) => <li key={i}>{i}</li>)}</ul></div>
);

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const toast = useToast();
  const { data: row, error, loading, reload } = useLoad(() => api<Detail>(`/incidents/${id}`), [id]);
  const [busy, setBusy] = useState<Action | "">("");

  async function act(action: Action) {
    setBusy(action);
    try { await api(`/incidents/${id}/${action}`, { method: "POST" }); toast("success", done[action]); await reload(); }
    catch (e) { toast("error", e instanceof Error ? e.message : "Action failed"); } finally { setBusy(""); }
  }

  if (loading && !row) return <PageSkeleton rows={2} />;
  if (error || !row) return <ErrorState message={error || "Incident not found"} onRetry={reload} />;

  return (
    <div className="space-y-6">
      <Link href="/incidents" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 no-underline hover:text-brand dark:text-slate-400"><ArrowLeft className="h-4 w-4" /> All incidents</Link>
      <PageHeader title={row.title} description={`${row.public_id} · ${row.category}`} actions={<><StatusBadge status={row.severity} /><StatusBadge status={row.status} />{row.is_simulated && <SyntheticBadge />}</>} />
      {row.is_simulated && <p className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm font-medium text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">Synthetic educational incident. No public website was contacted.</p>}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" loading={busy === "acknowledge"} onClick={() => act("acknowledge")}><Eye className="h-4 w-4" /> Acknowledge</Button>
        <Button loading={busy === "resolve"} onClick={() => act("resolve")}><CheckCheck className="h-4 w-4" /> Resolve</Button>
        <Button variant="secondary" loading={busy === "reopen"} onClick={() => act("reopen")}><RotateCcw className="h-4 w-4" /> Reopen</Button>
        <Button variant="secondary" loading={busy === "ai"} onClick={() => act("ai")}><Sparkles className="h-4 w-4" /> Refresh AI note</Button>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="card"><h2 className="font-semibold">Symptoms</h2><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{row.symptoms.map((s) => <li key={s}>{s}</li>)}</ul>
          <details className="mt-4"><summary className="cursor-pointer text-sm font-medium text-brand">Raw evidence</summary><pre className="mt-2 max-h-72 overflow-auto rounded-xl bg-slate-100 p-3 text-xs dark:bg-slate-950">{JSON.stringify(row.evidence, null, 2)}</pre></details></section>
        <section className="card"><h2 className="font-semibold">Timeline</h2>
          <ol className="relative mt-3 space-y-4 border-l border-slate-200 pl-5 text-sm dark:border-white/15">{row.timeline.map((e, i) => <li key={e.created_at + e.event_type + i}><span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-brand" /><p className="muted">{fmtDate(e.created_at)} · {e.actor}</p><p><strong>{e.event_type}</strong>: {e.message}</p></li>)}</ol></section>
      </div>
      {row.rca && (
        <section className="card"><h2 className="font-semibold">Root cause analysis</h2><p className="mt-2 text-sm">{row.rca.observed_problem}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">{row.rca.hypotheses.map((h) => (
            <article key={h.title} className="rounded-xl border border-slate-200 p-4 dark:border-white/10"><div className="flex flex-wrap gap-2"><Badge tone={h.status === "confirmed" ? "green" : "amber"}>{h.status}</Badge><Badge tone="indigo">{h.confidence} confidence</Badge></div><h3 className="mt-2 font-medium">{h.title}</h3><p className="muted mt-1">{h.explanation}</p>
              {h.evidence?.length > 0 && <ul className="muted mt-2 list-disc pl-5">{h.evidence.map((ev) => <li key={ev}>{ev}</li>)}</ul>}</article>))}</div>
          <List title="Verification" items={row.rca.verification_steps} /><List title="Suggested actions" items={row.rca.recommended_actions} /><List title="Preventive measures" items={row.rca.preventive_measures} />
        </section>
      )}
      {row.ai && (
        <section className="card"><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold">Explanation</h2><Badge tone="indigo">{row.ai.source}</Badge></div><p className="mt-2">{row.ai.content.summary}</p><p className="muted mt-2">{row.ai.content.confidence_note}</p>
          <List title="Likely causes" items={row.ai.content.likely_causes} /><List title="Troubleshooting steps" items={row.ai.content.troubleshooting_steps} /><List title="Preventive actions" items={row.ai.content.preventive_actions} /></section>
      )}
    </div>
  );
}
