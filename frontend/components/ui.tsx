"use client";

import { AlertTriangle, ArrowRight, CheckCircle2, Info, Loader2, X, XCircle } from "lucide-react";
import Link from "next/link";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from "react";

/* ---------- toasts ---------- */
type ToastKind = "success" | "error" | "info";
type ToastItem = { id: number; kind: ToastKind; message: string };
const ToastCtx = createContext<(kind: ToastKind, message: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((kind: ToastKind, message: string) => {
    const id = Date.now() + Math.random();
    setItems((cur) => [...cur.slice(-3), { id, kind, message }]);
    setTimeout(() => setItems((cur) => cur.filter((t) => t.id !== id)), kind === "error" ? 7000 : 4000);
  }, []);
  const icon = { success: <CheckCircle2 className="h-4 w-4 text-emerald-500" />, error: <XCircle className="h-4 w-4 text-red-500" />, info: <Info className="h-4 w-4 text-brand" /> };
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" role="status" className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-[calc(100vw-2rem)] max-w-sm flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} className="pointer-events-auto flex animate-toastin items-start gap-3 rounded-xl border border-slate-200 bg-white p-3 text-sm shadow-lg dark:border-white/10 dark:bg-slate-900">
            <span className="mt-0.5">{icon[t.kind]}</span>
            <p className="flex-1">{t.message}</p>
            <button aria-label="Dismiss notification" className="text-slate-400 hover:text-slate-700 dark:hover:text-white" onClick={() => setItems((c) => c.filter((x) => x.id !== t.id))}>
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

/* ---------- buttons ---------- */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean; variant?: "primary" | "secondary" | "danger" | "ghost"; arrow?: boolean };
const variantClass = { primary: "btn group", secondary: "btn-secondary group", danger: "btn-danger", ghost: "btn-ghost" };

export function Button({ loading, variant = "primary", arrow, children, className = "", disabled, type = "button", ...rest }: BtnProps) {
  return (
    <button type={type} className={`${variantClass[variant]} ${className}`} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
      {children}
      {arrow && !loading && <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" aria-hidden />}
    </button>
  );
}

export function LinkButton({ href, children, variant = "primary", arrow, className = "" }: { href: string; children: ReactNode; variant?: "primary" | "secondary"; arrow?: boolean; className?: string }) {
  return (
    <Link href={href} className={`${variantClass[variant]} ${className}`}>
      {children}
      {arrow && <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" aria-hidden />}
    </Link>
  );
}

/* ---------- feedback blocks ---------- */
export function Skeleton({ className = "h-4 w-full" }: { className?: string }) {
  return <div aria-hidden className={`skeleton ${className}`} />;
}

export function PageSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-6" role="status" aria-label="Loading">
      <Skeleton className="h-9 w-56" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}</div>
      {Array.from({ length: rows }).map((_, i) => <Skeleton key={i} className="h-40" />)}
    </div>
  );
}

export function Empty({ title, body, action, icon }: { title: string; body: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="card flex flex-col items-center px-6 py-10 text-center">
      {icon && <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-soft text-brand dark:bg-brand/15">{icon}</div>}
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="muted mt-1.5 max-w-md">{body}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="card flex flex-col items-start gap-3 border-red-200 bg-red-50/60 dark:border-red-900 dark:bg-red-950/30">
      <div className="flex items-center gap-2 font-semibold text-red-700 dark:text-red-400"><AlertTriangle className="h-4 w-4" /> Something went wrong</div>
      <p className="text-sm text-red-700/90 dark:text-red-300">{message}</p>
      {onRetry && <Button variant="secondary" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

export function ErrorText({ error }: { error: string }) {
  return error ? <p role="alert" className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p> : null;
}

export function Badge({ tone = "slate", children }: { tone?: "slate" | "green" | "red" | "amber" | "indigo" | "orange"; children: ReactNode }) {
  const tones = {
    slate: "bg-slate-100 text-slate-700 dark:bg-white/10 dark:text-slate-300",
    green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-300",
    red: "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300",
    amber: "bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-300",
    orange: "bg-orange-100 text-orange-800 dark:bg-orange-500/15 dark:text-orange-300",
    indigo: "bg-brand-soft text-brand-dark dark:bg-brand/20 dark:text-indigo-200",
  };
  return <span className={`badge ${tones[tone]}`}>{children}</span>;
}

export function statusTone(status: string): "green" | "red" | "amber" | "slate" {
  const s = status.toLowerCase();
  if (["healthy", "up", "ok", "resolved", "active"].includes(s)) return "green";
  if (["down", "critical", "high", "open", "issues", "degraded"].includes(s)) return "red";
  if (["medium", "warning", "acknowledged", "paused"].includes(s)) return "amber";
  return "slate";
}
export const StatusBadge = ({ status }: { status: string }) => <Badge tone={statusTone(status)}>{status}</Badge>;
export const SyntheticBadge = () => <Badge tone="amber">Synthetic</Badge>;

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold sm:text-3xl">{title}</h1>
        {description && <p className="muted mt-1 max-w-3xl">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

/* ---------- accessible dialog (native <dialog>: focus trap + Esc) ---------- */
export function Dialog({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);
  return (
    <dialog ref={ref} onClose={onClose} onClick={(e) => e.target === ref.current && onClose()} aria-labelledby="dlg-title" className="m-auto w-[calc(100vw-2rem)] max-w-md rounded-2xl border border-slate-200 bg-white p-0 text-slate-800 shadow-2xl backdrop:bg-ink/50 backdrop:backdrop-blur-sm open:animate-pop dark:border-white/10 dark:bg-slate-900 dark:text-slate-100">
      <div className="p-6">
        <h2 id="dlg-title" className="text-lg font-semibold">{title}</h2>
        <div className="mt-2">{children}</div>
      </div>
    </dialog>
  );
}

export function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel, loading }: { open: boolean; title: string; body: string; confirmLabel: string; onConfirm: () => void; onCancel: () => void; loading?: boolean }) {
  return (
    <Dialog open={open} onClose={onCancel} title={title}>
      <p className="muted">{body}</p>
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button variant="danger" loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Dialog>
  );
}

/* ---------- tabs ---------- */
export function Tabs({ tabs, value, onChange }: { tabs: { id: string; label: string }[]; value: string; onChange: (id: string) => void }) {
  return (
    <div role="tablist" className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1 dark:bg-white/5">
      {tabs.map((t) => (
        <button key={t.id} role="tab" type="button" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition ${value === t.id ? "bg-white text-brand shadow-sm dark:bg-slate-800 dark:text-white" : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

/* ---------- data loading hook ---------- */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await fnRef.current());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void reload(); }, deps);
  return { data, error, loading, reload, setData };
}

export const fmtDate = (value: string | null | undefined) => (value ? new Date(value).toLocaleString() : "—");
