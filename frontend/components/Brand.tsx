import Link from "next/link";

export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <defs>
        <linearGradient id="lg" x1="0" y1="0" x2="32" y2="32"><stop stopColor="#4F46E5" /><stop offset="1" stopColor="#06B6D4" /></linearGradient>
      </defs>
      <rect width="32" height="32" rx="9" fill="url(#lg)" />
      <path d="M4 17h6l3-7 4 13 3-9 2 3h6" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Brand({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2.5 no-underline" aria-label="Incident RCA home">
      <LogoMark />
      <span className="font-display text-lg font-bold text-slate-900 dark:text-white">Incident RCA</span>
    </Link>
  );
}
