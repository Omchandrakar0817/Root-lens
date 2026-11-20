"use client";

import { Activity, ArrowRight, Globe, ShieldAlert, ShieldCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Empty, ErrorState, LinkButton, PageHeader, PageSkeleton, StatusBadge, SyntheticBadge, fmtDate, useLoad } from "@/components/ui";
import { api } from "@/lib/api";
import { chartAxis, chartTip } from "@/lib/chart";

type Summary = {
  total_websites: number;
  healthy_websites: number;
  websites_with_issues: number;
  unknown_websites: number;
  active_incidents: number;
  uptime_percent: number | null;
  recent_incidents: { public_id: string; title: string; severity: string; is_simulated: boolean; detected_at: string }[];
  websites: { id: string; name: string; url: string; latest_status: string; latest_checked_at: string | null }[];
  response_series: { website: string; website_id: string; latest_response_time_ms: number | null; points: { checked_at: string; response_time_ms: number | null }[] }[];
  message: string | null;
};

export default function DashboardPage() {
  const { data, error, loading, reload } = useLoad(() => api<Summary>("/dashboard"));
  if (loading && !data) return <PageSkeleton rows={2} />;
  if (error || !data) return <ErrorState message={error || "No data returned"} onRetry={reload} />;

  const series = data.response_series.find((item) => item.points.some((point) => point.response_time_ms != null)) || null;
  const chart = (series?.points || []).filter((p) => p.response_time_ms != null).map((p) => ({ time: new Date(p.checked_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), ms: p.response_time_ms }));
  const latestResponse = series?.latest_response_time_ms;
  const cards = [
    { label: "Websites", value: data.total_websites, icon: Globe, tone: "text-brand bg-brand-soft dark:bg-brand/15" },
    { label: "Healthy", value: data.healthy_websites, icon: ShieldCheck, tone: "text-emerald-600 bg-emerald-50 dark:bg-emerald-500/15" },
    { label: "With issues", value: data.websites_with_issues, icon: TriangleAlert, tone: "text-orange-600 bg-orange-50 dark:bg-orange-500/15" },
    { label: "Active incidents", value: data.active_incidents, icon: ShieldAlert, tone: "text-red-600 bg-red-50 dark:bg-red-500/15" },
  ];

  if (data.total_websites === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="Overview" />
        <Empty icon={<Globe className="h-6 w-6" />} title="No websites yet" body="Add a public website to start collecting measurements. Charts and incidents appear after the first scan." action={<LinkButton href="/websites" arrow>Add your first website</LinkButton>} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Overview" description="Live figures from your stored measurements." actions={<LinkButton href="/websites" variant="secondary">Manage websites</LinkButton>} />
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Summary">
        {cards.map((c) => (
          <article key={c.label} className="card card-hover">
            <div className="flex items-center justify-between"><p className="muted">{c.label}</p><span className={`flex h-9 w-9 items-center justify-center rounded-xl ${c.tone}`}><c.icon className="h-4 w-4" /></span></div>
            <p className="mt-3 font-display text-3xl font-bold">{c.value}</p>
          </article>
        ))}
      </section>
      <section className="grid gap-4 lg:grid-cols-3">
        <article className="card lg:col-span-2">
          <div className="flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 font-semibold"><Activity className="h-4 w-4 text-brand" /> Response time{series ? ` · ${series.website}` : ""}</h2>{latestResponse != null && <Badge tone="slate">Latest {Math.round(latestResponse)} ms</Badge>}</div>
          {data.message ? <p className="muted mt-4">{data.message}</p> : chart.length === 0 ? <p className="muted mt-4">Response times appear after a successful scan.</p> : (
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chart}>
                  <defs><linearGradient id="rt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#4F46E5" stopOpacity=".3" /><stop offset="1" stopColor="#4F46E5" stopOpacity="0" /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.2} vertical={false} />
                  <XAxis dataKey="time" {...chartAxis} /><YAxis unit=" ms" width={64} {...chartAxis} />
                  <Tooltip {...chartTip} />
                  <Area type="monotone" dataKey="ms" name="Response" stroke="#4F46E5" strokeWidth={2} fill="url(#rt)" animationDuration={700} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </article>
        <article className="card">
          <h2 className="font-semibold">Uptime</h2>
          <p className="mt-3 font-display text-3xl font-bold">{data.uptime_percent == null ? "No samples yet" : `${data.uptime_percent}%`}</p>
          <p className="muted mt-2">Across measured samples. {data.unknown_websites} unknown site(s): a single failed check stays unknown until a second check confirms it.</p>
        </article>
      </section>
      <section className="card space-y-3">
        <div className="flex items-center justify-between"><h2 className="font-semibold">Monitored websites</h2><Link href="/websites" className="text-sm font-semibold text-brand">Manage websites</Link></div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.websites.map((website) => (
            <Link key={website.id} href={`/websites/${website.id}`} className="rounded-xl border border-slate-200 p-3 no-underline hover:border-brand dark:border-white/10">
              <div className="flex items-start justify-between gap-2"><span className="min-w-0"><strong className="block truncate">{website.name}</strong><span className="muted block break-all text-xs">{website.url}</span></span><StatusBadge status={website.latest_status} /></div>
              <p className="muted mt-2 text-xs">Last scan: {website.latest_checked_at ? fmtDate(website.latest_checked_at) : "Not checked"}</p>
            </Link>
          ))}
        </div>
      </section>
      <article className="card">
        <div className="flex items-center justify-between"><h2 className="font-semibold">Recent incidents</h2><Link href="/incidents" className="inline-flex items-center gap-1 text-sm font-semibold text-brand">All incidents <ArrowRight className="h-3.5 w-3.5" /></Link></div>
        {data.recent_incidents.length === 0 ? <p className="muted mt-3">No open incidents. Synthetic simulator results are kept on the Simulator page.</p> : (
          <ul className="mt-3 divide-y divide-slate-200/80 dark:divide-white/10">
            {data.recent_incidents.map((i) => (
              <li key={i.public_id}><Link href="/incidents" className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm no-underline hover:text-brand"><span><strong>{i.public_id}</strong> · {i.title}</span><span className="flex items-center gap-2"><StatusBadge status={i.severity} />{i.is_simulated && <SyntheticBadge />}<span className="muted">{fmtDate(i.detected_at)}</span></span></Link></li>
            ))}
          </ul>
        )}
      </article>
    </div>
  );
}
