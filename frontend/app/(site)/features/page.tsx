import type { Metadata } from "next";
import { LinkButton } from "@/components/ui";
import { features } from "@/lib/content";

export const metadata: Metadata = { title: "Features" };

export default function FeaturesPage() {
  return (
    <div className="container-x py-16">
      <h1 className="max-w-2xl text-4xl font-bold">Features</h1>
      <p className="muted mt-3 max-w-2xl text-base">What each part of the platform does, and what it needs to run.</p>
      <div className="mt-10 grid gap-5 md:grid-cols-2">
        {features.map((f) => (
          <article key={f.title} className="card card-hover flex gap-4">
            <div className="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-brand-soft text-brand dark:bg-brand/15 dark:text-indigo-300"><f.icon className="h-5 w-5" /></div>
            <div><h2 className="text-lg font-semibold">{f.title}</h2><p className="muted mt-1.5 text-[0.95rem]">{f.detail}</p></div>
          </article>
        ))}
      </div>
      <section className="card mt-8" aria-labelledby="extras-h">
        <h2 id="extras-h" className="text-lg font-semibold">Also included</h2>
        <ul className="muted mt-3 list-disc space-y-1.5 pl-5 text-[0.95rem]">
          <li><strong className="text-slate-800 dark:text-slate-200">AI explanations.</strong> Gemini is used only when a key is configured on the server. Otherwise a rule-based explanation is generated and labeled as rule-based.</li>
          <li><strong className="text-slate-800 dark:text-slate-200">Incident simulator.</strong> Generates clearly labeled synthetic incidents for learning. It sends no traffic to any real website and is excluded from live uptime.</li>
          <li><strong className="text-slate-800 dark:text-slate-200">Optional monitoring agent.</strong> Reports CPU, memory and disk only from a machine you own and install it on.</li>
        </ul>
      </section>
      <div className="mt-10"><LinkButton href="/register" arrow>Start monitoring</LinkButton></div>
    </div>
  );
}
