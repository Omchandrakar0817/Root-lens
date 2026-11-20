import type { Metadata } from "next";
import { LinkButton } from "@/components/ui";

export const metadata: Metadata = { title: "About" };

const tech = [
  ["Frontend", "Next.js, React, TypeScript, Tailwind CSS, Recharts"],
  ["Backend", "FastAPI (Python)"],
  ["Data", "Supabase PostgreSQL, Upstash Redis"],
  ["Scheduling", "Celery worker and Celery Beat"],
  ["Analysis", "Isolation Forest anomaly detection, rule-based RCA, Google Gemini, Google PageSpeed Insights"],
];

export default function AboutPage() {
  return (
    <div className="container-x max-w-4xl py-16">
      <h1 className="text-4xl font-bold">About this project</h1>
      <p className="mt-4 text-lg text-slate-600 dark:text-slate-300">
        Incident RCA is a final-year engineering project: an AI-based incident prediction and root cause analysis system for application monitoring.
      </p>
      <div className="mt-10 space-y-8">
        <section><h2 className="text-2xl font-bold">The problem</h2><p className="muted mt-2 text-base">Basic uptime checks tell you a site is down, but not why. Teams then spend time matching symptoms to causes by hand, and noisy alerts make real incidents easy to miss.</p></section>
        <section>
          <h2 className="text-2xl font-bold">Objectives</h2>
          <ul className="muted mt-2 list-disc space-y-1 pl-5 text-base">
            <li>Collect real availability, security, SEO and performance measurements for public websites.</li>
            <li>Detect abnormal behavior from each site’s own history.</li>
            <li>Explain incidents with ranked, evidence-backed hypotheses.</li>
            <li>Keep confirmed facts, hypotheses and synthetic data clearly separate.</li>
          </ul>
        </section>
        <section><h2 className="text-2xl font-bold">How AI helps</h2><p className="muted mt-2 text-base">A machine-learning model flags measurements that deviate from a site’s normal pattern. A rule-based engine ranks likely causes from the evidence. Gemini turns that evidence into a plain-language explanation when it is available, and the system falls back to rule-based text when it is not.</p></section>
        <section>
          <h2 className="text-2xl font-bold">Technology</h2>
          <dl className="mt-3 divide-y divide-slate-200 rounded-2xl border border-slate-200 dark:divide-white/10 dark:border-white/10">
            {tech.map(([k, v]) => (
              <div key={k} className="grid gap-1 px-4 py-3 sm:grid-cols-[9rem_1fr]"><dt className="text-sm font-semibold">{k}</dt><dd className="muted">{v}</dd></div>
            ))}
          </dl>
        </section>
      </div>
      <div className="mt-10 flex gap-3"><LinkButton href="/how-it-works" variant="secondary">How it works</LinkButton><LinkButton href="/contact">Contact</LinkButton></div>
    </div>
  );
}
