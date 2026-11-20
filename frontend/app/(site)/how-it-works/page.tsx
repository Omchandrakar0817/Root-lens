import type { Metadata } from "next";
import { LinkButton } from "@/components/ui";
import { steps } from "@/lib/content";

export const metadata: Metadata = { title: "How it works" };

const pipeline = ["Your browser", "FastAPI backend", "Supabase database", "Celery worker", "Analysis and AI"];

export default function HowItWorksPage() {
  return (
    <div className="container-x py-16">
      <h1 className="max-w-2xl text-4xl font-bold">How it works</h1>
      <p className="muted mt-3 max-w-2xl text-base">The path from a URL to an explained incident.</p>

      <ol className="mt-10 space-y-4">
        {steps.map((s, i) => (
          <li key={s.title} className="card flex gap-4">
            <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-gradient-to-br from-brand to-pulse font-bold text-white">{i + 1}</span>
            <div><h2 className="text-lg font-semibold">{s.title}</h2><p className="muted mt-1 text-[0.95rem]">{s.body}</p></div>
          </li>
        ))}
      </ol>

      <section className="mt-14" aria-labelledby="arch-h">
        <h2 id="arch-h" className="text-2xl font-bold">Under the hood</h2>
        <div className="mt-5 flex flex-col items-stretch gap-2 md:flex-row md:items-center">
          {pipeline.map((p, i) => (
            <div key={p} className="flex flex-1 items-center gap-2 md:flex-col md:gap-0">
              <div className="card w-full !p-4 text-center text-sm font-semibold">{p}</div>
              {i < pipeline.length - 1 && <span aria-hidden className="text-slate-400 md:my-1 md:rotate-90">→</span>}
            </div>
          ))}
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <article className="card"><h3 className="font-semibold">Detection</h3><p className="muted mt-1.5">With fewer than 30 samples, the system uses a statistical check and reports that no model was trained. With enough samples it trains an Isolation Forest on that website’s own history. Linear forecasts are stored only after 20 response-time samples.</p></article>
          <article className="card"><h3 className="font-semibold">Explanation</h3><p className="muted mt-1.5">Root-cause hypotheses are built from stored evidence. Gemini adds a plain-language summary when it is configured and has quota. If not, a rule-based summary is used and labeled.</p></article>
        </div>
      </section>
      <div className="mt-10"><LinkButton href="/register" arrow>Start monitoring</LinkButton></div>
    </div>
  );
}
