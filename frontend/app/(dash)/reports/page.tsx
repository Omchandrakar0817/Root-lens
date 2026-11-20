"use client";

import { Download, FileText } from "lucide-react";
import { useState } from "react";
import { Button, ErrorState, PageHeader, PageSkeleton, SyntheticBadge, fmtDate, useLoad, useToast } from "@/components/ui";
import { api } from "@/lib/api";

type Report = { id: string; title: string; created_at: string };
type Full = Report & { content: { sections: { website: string; url: string; status: string; latest_checked_at?: string | null; samples: number; uptime_percent: number | null; incidents: { public_id: string; title: string; severity?: string; status?: string; symptoms?: string[]; simulated: boolean }[]; recent_scans?: { status: string; trigger: string; created_at: string; simulated: boolean }[]; rca?: { incident: string; observed_problem: string; hypotheses: unknown[]; recommended_actions: string[]; preventive_measures: string[] }[]; ai_insights?: { incident: string; source: string; content: Record<string, unknown> }[] }[] } };

export default function ReportsPage() {
  const toast = useToast();
  const { data: rows, error, loading, reload } = useLoad(() => api<Report[]>("/reports"));
  const [current, setCurrent] = useState<Full | null>(null);
  const [creating, setCreating] = useState(false);
  const [opening, setOpening] = useState("");

  async function create() {
    setCreating(true);
    try { setCurrent(await api<Full>("/reports", { method: "POST", body: JSON.stringify({ title: "Website health report" }) })); toast("success", "Report generated from stored data."); await reload(); }
    catch (e) { toast("error", e instanceof Error ? e.message : "Could not generate report"); } finally { setCreating(false); }
  }
  async function open(id: string) {
    setOpening(id);
    try { setCurrent(await api<Full>(`/reports/${id}`)); } catch (e) { toast("error", e instanceof Error ? e.message : "Could not open report"); } finally { setOpening(""); }
  }
  function download() {
    if (!current) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(current.content, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url; a.download = `${current.title.replace(/\s+/g, "-").toLowerCase()}.json`; a.click();
    URL.revokeObjectURL(url);
  }

  if (loading && !rows) return <PageSkeleton rows={1} />;
  if (error || !rows) return <ErrorState message={error || "No data"} onRetry={reload} />;
  return (
    <div className="space-y-6">
      <PageHeader title="Reports" description="Reports summarize websites and incidents already in the database. They do not invent uptime." actions={<Button loading={creating} onClick={create}><FileText className="h-4 w-4" /> Generate from stored data</Button>} />
      <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
        <aside className="card !p-2" aria-label="Saved reports">
          {rows.length === 0 ? <p className="muted p-3">No reports yet.</p> : rows.map((r) => (
            <button key={r.id} type="button" disabled={opening === r.id} onClick={() => open(r.id)} className={`block w-full rounded-xl px-3 py-2.5 text-left text-sm transition hover:bg-slate-100 dark:hover:bg-white/10 ${current?.id === r.id ? "bg-brand-soft dark:bg-brand/15" : ""}`}>
              {r.title}<span className="muted block">{fmtDate(r.created_at)}</span>
            </button>))}
        </aside>
        <section className="card">
          {!current ? <p className="muted">Generate or open a report.</p> : (<>
            <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">{current.title}</h2><Button variant="secondary" onClick={download}><Download className="h-4 w-4" /> Download JSON</Button></div>
            <div className="mt-4 space-y-4">{current.content.sections.length === 0 ? <p className="muted">No live websites to include.</p> : current.content.sections.map((s) => (
              <article key={s.url} className="rounded-xl border border-slate-200 p-4 dark:border-white/10"><h3 className="font-medium">{s.website}</h3><p className="muted break-all">{s.url} · {s.status} · samples {s.samples} · uptime {s.uptime_percent ?? "n/a"}</p><p className="muted text-xs">Last scan: {s.latest_checked_at ? fmtDate(s.latest_checked_at) : "Not checked"}</p>
                <p className="mt-2 text-sm">Recent scans: {(s.recent_scans || []).length}</p><p className="muted text-xs">RCA records: {(s.rca || []).length} · AI insights: {(s.ai_insights || []).length}</p>
                <ul className="mt-2 space-y-1 text-sm">{s.incidents.map((i) => <li key={i.public_id}>{i.public_id}: {i.title} {i.simulated && <SyntheticBadge />}</li>)}</ul></article>))}</div>
          </>)}
        </section>
      </div>
    </div>
  );
}
