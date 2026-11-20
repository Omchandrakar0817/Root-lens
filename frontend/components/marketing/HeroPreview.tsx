import { Activity, ShieldCheck } from "lucide-react";

/** Illustrative preview. Values are sample data and labeled as such. */
export function HeroPreview() {
  const d = "M0 92 L40 88 L80 90 L120 84 L160 86 L200 80 L240 83 L280 78 L300 30 L320 18 L340 74 L380 80 L420 76 L460 79 L500 74 L540 77";
  return (
    <div className="card relative overflow-hidden p-0" role="img" aria-label="Illustrative sample of the monitoring dashboard. Not live data.">
      <div className="flex items-center justify-between border-b border-slate-200/80 px-5 py-3 dark:border-white/10">
        <div className="flex items-center gap-2 text-sm font-semibold"><Activity className="h-4 w-4 text-brand" /> Response time</div>
        <span className="badge bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300">Sample data</span>
      </div>
      <div className="p-5">
        <svg viewBox="0 0 540 120" className="h-36 w-full" aria-hidden>
          <defs>
            <linearGradient id="hp" x1="0" x2="1"><stop stopColor="#4F46E5" /><stop offset="1" stopColor="#06B6D4" /></linearGradient>
            <linearGradient id="hf" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#4F46E5" stopOpacity=".18" /><stop offset="1" stopColor="#4F46E5" stopOpacity="0" /></linearGradient>
          </defs>
          <path d={`${d} L540 120 L0 120 Z`} fill="url(#hf)" />
          <path d={d} className="trace animate-draw" fill="none" stroke="url(#hp)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="320" cy="18" r="5" fill="#F59E0B" />
        </svg>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 dark:border-amber-500/30 dark:bg-amber-500/10">
            <p className="text-xs font-semibold text-amber-800 dark:text-amber-300">Anomaly detected</p>
            <p className="mt-0.5 text-sm">Response time rose far above the site’s baseline.</p>
          </div>
          <div className="rounded-xl border border-slate-200 p-3 dark:border-white/10">
            <p className="flex items-center gap-1.5 text-xs font-semibold"><ShieldCheck className="h-3.5 w-3.5 text-emerald-500" /> Root cause hypotheses</p>
            <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">Ranked, with the evidence for each.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
