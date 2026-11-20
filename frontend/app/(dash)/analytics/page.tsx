"use client";

import { BarChart3 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Empty, ErrorState, PageHeader, PageSkeleton, SyntheticBadge, useLoad } from "@/components/ui";
import { api } from "@/lib/api";
import { chartAxis, chartTip } from "@/lib/chart";

type Point = { id: string; website_id: string; metric: string; method: string; model_trained: boolean; score: number | null; is_anomaly: boolean; value: number | null; baseline: number | null; evidence: { note?: string; sample_count?: number; horizon_steps?: number; slope_per_step?: number }; is_simulated: boolean; detected_at: string };
type Data = { anomalies: Point[]; forecasts: Point[]; message: string };
type Site = { id: string; name: string; url: string };
type Availability = { points: { checked_at: string; response_time_ms: number | null }[] };

function ActualLineChart({ points }: { points: Availability["points"] }) {
  const actual = [...points].reverse().filter((point) => point.response_time_ms != null);
  if (actual.length < 2) return null;
  const chart = actual.map((point, index) => ({ time: `Actual ${index + 1}`, actual: point.response_time_ms as number }));
  return <div className="mt-4 h-56"><ResponsiveContainer width="100%" height="100%"><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.2} vertical={false} /><XAxis dataKey="time" minTickGap={24} {...chartAxis} /><YAxis unit=" ms" width={64} {...chartAxis} /><Tooltip {...chartTip} /><Legend /><Line type="monotone" dataKey="actual" name="Actual" stroke="#4F46E5" strokeWidth={2} dot={{ r: 2, fill: "#4F46E5" }} /></LineChart></ResponsiveContainer></div>;
}

function ForecastLineChart({ forecast }: { forecast: Point }) {
  const slope = forecast.score;
  if (forecast.value == null || slope == null) return null;
  const horizonSteps = forecast.evidence?.horizon_steps || 6;
  const chart = Array.from({ length: horizonSteps }, (_, index) => {
    const step = index + 1;
    const projected = Math.round((forecast.value as number - slope * (horizonSteps - step)) * 1000) / 1000;
    return { time: `Forecast ${step}`, forecast: projected };
  });
  return <div className="mt-4 h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.2} vertical={false} /><XAxis dataKey="time" minTickGap={24} {...chartAxis} /><YAxis unit=" ms" width={64} {...chartAxis} /><Tooltip {...chartTip} /><Legend /><Line type="linear" dataKey="forecast" name="Forecast" stroke="#10b981" strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3, fill: "#10b981" }} /></LineChart></ResponsiveContainer></div>;
}

export default function AnalyticsPage() {
  const { data, error, loading, reload } = useLoad(async () => {
    const [analytics, sites] = await Promise.all([api<Data>("/analytics"), api<Site[]>("/websites")]);
    const histories = await Promise.all(sites.map(async (site) => [site.id, await api<Availability>(`/websites/${site.id}/availability`)] as const));
    return { analytics, sites, histories: Object.fromEntries(histories) };
  });
  if (loading && !data) return <PageSkeleton rows={1} />;
  if (error || !data) return <ErrorState message={error || "No data"} onRetry={reload} />;
  const analytics = data.analytics;
  const chart = analytics.anomalies.filter((i) => !i.is_simulated && i.score != null).slice(0, 12).reverse().map((i) => ({ label: new Date(i.detected_at).toLocaleDateString(), score: i.score }));
  return (
    <div className="space-y-6">
      <PageHeader title="ML analytics" description={analytics.message} />
      <section className="grid gap-3 md:grid-cols-2">{data.sites.map((site) => {
        const anomalies = analytics.anomalies.filter((point) => point.website_id === site.id && !point.is_simulated);
        const forecasts = analytics.forecasts.filter((point) => point.website_id === site.id && !point.is_simulated);
        const points = [...(data.histories[site.id]?.points || [])].reverse().filter((point) => point.response_time_ms != null);
        const sampleCount = points.length;
        const forecast = forecasts[0];
        const history = data.histories[site.id]?.points || [];
        return <article key={site.id} className="card"><div className="flex items-start justify-between gap-2"><div><h2 className="font-semibold">{site.name}</h2><p className="muted break-all text-xs">{site.url}</p></div><Badge tone={anomalies.some((point) => point.is_anomaly) ? "orange" : "green"}>{anomalies.some((point) => point.is_anomaly) ? "Anomaly detected" : "Normal"}</Badge></div><p className="mt-3 text-sm"><strong>{sampleCount}</strong> real response-time samples · <strong>{anomalies.filter((point) => point.model_trained).length}</strong> trained model result(s)</p>
          <ActualLineChart points={history} />
          {forecast?.value != null ? <p className="muted mt-3 text-xs">Forecast details are shown in the Forecasts section.</p> : <><p className="muted mt-3 text-xs">Forecast progress: {Math.min(sampleCount, 20)} / 20 real samples</p><div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-white/10"><div className="h-full rounded-full bg-brand" style={{ width: `${Math.min(100, sampleCount / 20 * 100)}%` }} /></div></>}
        </article>;
      })}</section>
      {analytics.anomalies.length === 0 && analytics.forecasts.length === 0 && <Empty icon={<BarChart3 className="h-6 w-6" />} title="No model output" body="Scan a website a few times. With fewer than 30 samples the page shows a statistical check and model trained stays false." />}
      {chart.length > 0 && (
        <article className="card"><h2 className="font-semibold">Recent anomaly scores</h2>
          <div className="mt-4 h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#94a3b8" strokeOpacity={0.2} vertical={false} /><XAxis dataKey="label" {...chartAxis} /><YAxis width={48} {...chartAxis} /><Tooltip {...chartTip} /><Bar dataKey="score" name="Score" fill="#4F46E5" radius={[6, 6, 0, 0]} animationDuration={700} /></BarChart></ResponsiveContainer></div></article>
      )}
      {analytics.anomalies.length > 0 && <section className="grid gap-3 md:grid-cols-2">{analytics.anomalies.map((i) => (
        <article key={i.id} className="card"><div className="flex flex-wrap gap-2"><Badge tone="slate">{i.method}</Badge><Badge tone={i.model_trained ? "indigo" : "slate"}>{i.model_trained ? "model trained" : "no model yet"}</Badge>{i.is_anomaly ? <Badge tone="orange">Anomaly</Badge> : <Badge tone="green">Normal</Badge>}{i.is_simulated && <SyntheticBadge />}</div>
          <p className="mt-2 text-sm">Value {i.value ?? "—"} · baseline {i.baseline ?? "—"} · score {i.score ?? "—"}</p><p className="muted">{i.evidence?.note}</p></article>))}</section>}
      <section className="space-y-3"><h2 className="text-xl font-semibold">Forecasts</h2>
        {analytics.forecasts.length === 0 ? <p className="muted">No forecast. A linear projection is stored only after 20 response-time samples.</p> : (() => {
          const latestByWebsite = new Map<string, Point>();
          for (const forecast of analytics.forecasts) if (!latestByWebsite.has(forecast.website_id)) latestByWebsite.set(forecast.website_id, forecast);
          return Array.from(latestByWebsite.entries()).map(([websiteId, forecast]) => {
            const site = data.sites.find((item) => item.id === websiteId);
            const slope = forecast.score;
            const trend = slope == null ? null : slope > 0 ? "Rising trend" : slope < 0 ? "Falling trend" : "Flat trend";
            const history = data.histories[websiteId]?.points || [];
            return <article key={forecast.id} className="card"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-semibold">{site?.name || "Monitored website"}</h3><p className="muted break-all text-xs">{site?.url}</p></div><div className="flex flex-wrap gap-2"><Badge tone="indigo">Projected latency: {forecast.value} ms</Badge><Badge tone="slate">Slope: {forecast.score} ms/step</Badge><Badge tone={trend === "Rising trend" ? "orange" : "green"}>{trend}</Badge></div></div><ForecastLineChart forecast={forecast} /><p className="muted mt-2 text-xs">Based on {forecast.evidence?.sample_count ?? history.filter((point) => point.response_time_ms != null).length} real response-time samples.</p></article>;
          });
        })()}</section>
    </div>
  );
}
