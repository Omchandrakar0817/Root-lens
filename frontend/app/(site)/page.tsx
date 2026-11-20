import { Check } from "lucide-react";
import Link from "next/link";
import { HeroPreview } from "@/components/marketing/HeroPreview";
import { LinkButton } from "@/components/ui";
import { benefits, features, steps } from "@/lib/content";

export default function HomePage() {
  return (
    <>
      <section className="relative overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-gradient-to-r from-brand/25 via-pulse/20 to-indigo-400/20 blur-3xl" />
        <div className="container-x relative grid items-center gap-12 py-16 lg:grid-cols-[1.05fr_1fr] lg:py-24">
          <div className="animate-rise">
            <h1 className="text-4xl font-bold leading-[1.08] sm:text-5xl lg:text-6xl">Know why your website broke, not just that it did.</h1>
            <p className="mt-5 max-w-xl text-lg text-slate-600 dark:text-slate-300">
              Add a public website, scan it safely, and get confirmed incidents with ranked, evidence-backed root causes. Anomaly detection learns from your own measurements.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <LinkButton href="/register" arrow>Start monitoring</LinkButton>
              <LinkButton href="/features" variant="secondary">Explore features</LinkButton>
            </div>
            <p className="muted mt-5">CPU and memory appear only if you install the optional agent on a server you own. URL scans never invent them.</p>
          </div>
          <div className="animate-rise [animation-delay:150ms]"><HeroPreview /></div>
        </div>
      </section>

      <section className="container-x py-16" aria-labelledby="features-h">
        <div className="max-w-2xl">
          <h2 id="features-h" className="text-3xl font-bold">Everything the monitor does, and only that</h2>
          <p className="muted mt-2 text-base">Each capability below is implemented in the app. Features that depend on server configuration say so.</p>
        </div>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <article key={f.title} className="card card-hover">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-soft text-brand dark:bg-brand/15 dark:text-indigo-300"><f.icon className="h-5 w-5" /></div>
              <h3 className="mt-4 text-base font-semibold">{f.title}</h3>
              <p className="muted mt-1.5">{f.short}</p>
            </article>
          ))}
        </div>
        <div className="mt-8"><Link href="/features" className="text-sm font-semibold text-brand">See how each feature works</Link></div>
      </section>

      <section className="container-x py-16" aria-labelledby="how-h">
        <h2 id="how-h" className="max-w-2xl text-3xl font-bold">From a URL to an explained incident in six steps</h2>
        <ol className="relative mt-10 grid gap-6 md:grid-cols-3">
          {steps.map((s, i) => (
            <li key={s.title} className="card relative">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand to-pulse text-sm font-bold text-white">{i + 1}</span>
              <h3 className="mt-3 text-base font-semibold">{s.title}</h3>
              <p className="muted mt-1.5">{s.body}</p>
            </li>
          ))}
        </ol>
        <div className="mt-8"><Link href="/how-it-works" className="text-sm font-semibold text-brand">Read the full walkthrough</Link></div>
      </section>

      <section className="container-x py-16" aria-labelledby="benefits-h">
        <h2 id="benefits-h" className="max-w-2xl text-3xl font-bold">Built for developers who need answers they can trust</h2>
        <ul className="mt-8 grid gap-4 sm:grid-cols-2">
          {benefits.map((b) => (
            <li key={b.title} className="flex gap-3 rounded-2xl border border-slate-200/80 p-5 dark:border-white/10">
              <Check className="mt-0.5 h-5 w-5 flex-none text-emerald-500" aria-hidden />
              <div><h3 className="text-base font-semibold">{b.title}</h3><p className="muted mt-1">{b.body}</p></div>
            </li>
          ))}
        </ul>
      </section>

      <section className="container-x pt-8">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-ink via-indigo-950 to-brand-dark p-10 text-center text-white sm:p-14">
          <h2 className="mx-auto max-w-xl text-3xl font-bold !text-white">Add your first website and run a scan</h2>
          <p className="mx-auto mt-3 max-w-lg text-indigo-100">Create an account, add a public URL, and run a scan to see real measurements.</p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <LinkButton href="/register" arrow className="!bg-white !from-white !to-white !text-brand-dark">Create account</LinkButton>
            <LinkButton href="/login" variant="secondary" className="!border-white/30 !bg-transparent !text-white hover:!bg-white/10">Log in</LinkButton>
          </div>
        </div>
      </section>
    </>
  );
}
