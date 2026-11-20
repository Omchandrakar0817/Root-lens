"use client";

import { FlaskConical, Play } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Button, ErrorState, PageHeader, PageSkeleton, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Scenario = { id: string; title: string; description: string };
type Run = { id: string; scenario: string; label: string; incident_id: string | null; created_at: string };

export default function SimulatorPage() {
  const toast = useToast();
  const [running, setRunning] = useState("");
  const { data, error, loading, reload } = useLoad(async () => {
    const [scenarios, runs] = await Promise.all([api<Scenario[]>("/simulator/scenarios"), api<Run[]>("/simulator/runs")]);
    return { scenarios, runs };
  });

  async function run(id: string) {
    setRunning(id);
    try {
      const r = await api<{ incident_id: string | null }>("/simulator/run", { method: "POST", body: JSON.stringify({ scenario: id }) });
      toast("success", r.incident_id ? "Synthetic incident created. It is labeled and excluded from live uptime." : "Scenario finished without an incident.");
      await reload();
    } catch (e) { toast("error", e instanceof Error ? e.message : "Simulation failed"); } finally { setRunning(""); }
  }

  if (loading && !data) return <PageSkeleton rows={1} />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={reload} />;
  return (
    <div className="space-y-6">
      <PageHeader title="Incident simulator" />
      <p className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">These scenarios generate synthetic measurements inside the database. They do not send traffic to a real website.</p>
      <div className="grid gap-4 md:grid-cols-2">{data.scenarios.map((s) => (
        <article key={s.id} className="card card-hover"><h2 className="flex items-center gap-2 font-semibold"><FlaskConical className="h-4 w-4 text-brand" /> {s.title}</h2><p className="muted mt-2">{s.description}</p><Button className="mt-4" loading={running === s.id} disabled={!!running} onClick={() => run(s.id)}><Play className="h-4 w-4" /> Run simulation</Button></article>
      ))}</div>
      <section className="card"><h2 className="font-semibold">Past synthetic runs</h2>
        {data.runs.length === 0 ? <p className="muted mt-2">No runs yet.</p> : <ul className="mt-3 divide-y divide-slate-200/70 text-sm dark:divide-white/10">{data.runs.map((r) => <li key={r.id} className="flex flex-wrap justify-between gap-2 py-2.5"><span>{fmtDate(r.created_at)} · {r.scenario} · {r.label}</span>{r.incident_id ? <Link href={`/incidents/${r.incident_id}`} className="font-semibold text-brand">Open incident</Link> : <span className="muted">No incident</span>}</li>)}</ul>}
      </section>
    </div>
  );
}
