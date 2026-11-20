"use client";

import { Bell, BarChart3, Brain, FileText, FlaskConical, Globe, LayoutDashboard, LogOut, Menu, Settings, Siren, Stethoscope, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, loadSession, logoutSession, type User } from "@/lib/api";
import { Brand } from "./Brand";
import { ThemeToggle } from "./ThemeToggle";

export { Empty, ErrorText } from "./ui";

const links = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/websites", label: "Websites", icon: Globe },
  { href: "/incidents", label: "Incidents", icon: Siren },
  { href: "/rca", label: "Root cause", icon: Stethoscope },
  { href: "/insights", label: "AI insights", icon: Brain },
  { href: "/analytics", label: "ML analytics", icon: BarChart3 },
  { href: "/simulator", label: "Simulator", icon: FlaskConical },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [drawer, setDrawer] = useState(false);
  const [menu, setMenu] = useState(false);
  const [openIncidents, setOpenIncidents] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const session = loadSession();
    if (!session) {
      router.replace("/login");
      return;
    }
    setUser(session.user);
    api<{ active_incidents: number }>("/dashboard").then((d) => setOpenIncidents(d.active_incidents)).catch(() => setOpenIncidents(null));
  }, [router, pathname]);

  useEffect(() => setDrawer(false), [pathname]);
  useEffect(() => {
    const close = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(false); };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && (setMenu(false), setDrawer(false));
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", esc); };
  }, []);

  async function logout() {
    await logoutSession();
    router.replace("/");
  }

  if (!user) return <main className="flex min-h-screen items-center justify-center"><p className="muted" role="status">Checking session…</p></main>;

  const sidebar = (
    <nav aria-label="Dashboard" className="flex flex-col gap-1">
      {links.map(({ href, label, icon: Icon }) => {
        const active = pathname.startsWith(href);
        return (
          <Link key={href} href={href} aria-current={active ? "page" : undefined}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium no-underline transition ${active ? "bg-brand text-white shadow-md shadow-brand/30" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/10"}`}>
            <Icon className="h-4 w-4" aria-hidden /> {label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
      <aside className="hidden border-r border-slate-200/80 bg-white/70 p-4 dark:border-white/10 dark:bg-slate-950/40 lg:block">
        <div className="sticky top-4 space-y-6"><Brand href="/dashboard" />{sidebar}</div>
      </aside>

      {drawer && <div className="fixed inset-0 z-40 bg-ink/50 backdrop-blur-sm lg:hidden" onClick={() => setDrawer(false)} aria-hidden />}
      <aside className={`fixed inset-y-0 left-0 z-50 w-72 transform overflow-y-auto bg-white p-4 shadow-2xl transition-transform duration-300 dark:bg-slate-950 lg:hidden ${drawer ? "translate-x-0" : "-translate-x-full"}`} {...(!drawer ? { inert: true } : {})} aria-label="Navigation drawer">
        <div className="mb-6 flex items-center justify-between"><Brand href="/dashboard" /><button className="btn-ghost !px-2" aria-label="Close navigation" onClick={() => setDrawer(false)}><X className="h-5 w-5" /></button></div>
        {sidebar}
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-slate-200/80 bg-white/75 px-4 backdrop-blur-xl dark:border-white/10 dark:bg-ink/75 md:px-8">
          <button className="btn-ghost !px-2.5 lg:hidden" aria-label="Open navigation" onClick={() => setDrawer(true)}><Menu className="h-5 w-5" /></button>
          <div className="flex-1" />
          <Link href="/incidents?status=open" className="btn-ghost relative !px-2.5" aria-label={openIncidents ? `${openIncidents} open incidents` : "Incidents"}>
            <Bell className="h-4 w-4" />
            {!!openIncidents && <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">{openIncidents}</span>}
          </Link>
          <ThemeToggle />
          <div className="relative" ref={menuRef}>
            <button className="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-white/10" aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu(!menu)}>
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand to-pulse text-sm font-bold text-white">{user.full_name.charAt(0).toUpperCase()}</span>
              <span className="hidden max-w-[9rem] truncate text-sm font-medium sm:block">{user.full_name}</span>
            </button>
            {menu && (
              <div role="menu" className="absolute right-0 mt-2 w-56 animate-pop rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl dark:border-white/10 dark:bg-slate-900">
                <p className="truncate px-3 py-2 text-xs text-slate-500">{user.email}</p>
                <Link role="menuitem" href="/settings" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm no-underline hover:bg-slate-100 dark:hover:bg-white/10"><Settings className="h-4 w-4" /> Account settings</Link>
                <Link role="menuitem" href="/" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm no-underline hover:bg-slate-100 dark:hover:bg-white/10"><Globe className="h-4 w-4" /> Public site</Link>
                <button role="menuitem" className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-white/10" onClick={logout}><LogOut className="h-4 w-4" /> Log out</button>
              </div>
            )}
          </div>
        </header>
        <main id="main" className="mx-auto max-w-6xl p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
