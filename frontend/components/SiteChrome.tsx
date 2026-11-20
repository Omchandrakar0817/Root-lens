"use client";

import { LayoutDashboard, LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { logoutSession } from "@/lib/api";
import { useSessionUser } from "@/lib/useSession";
import { Brand } from "./Brand";
import { ThemeToggle } from "./ThemeToggle";
import { LinkButton } from "./ui";

const nav = [
  { href: "/", label: "Home" },
  { href: "/features", label: "Features" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const user = useSessionUser();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [pathname]);

  async function logout() {
    await logoutSession();
    setOpen(false);
    router.replace("/");
    router.refresh();
  }
  const active = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/70 bg-white/75 backdrop-blur-xl dark:border-white/10 dark:bg-ink/75">
      <div className="container-x flex h-16 items-center justify-between gap-4">
        <Brand />
        <nav aria-label="Main" className="hidden items-center gap-1 lg:flex">
          {nav.map((item) => (
            <Link key={item.href} href={item.href} aria-current={active(item.href) ? "page" : undefined}
              className={`group relative px-3 py-2 text-sm font-medium no-underline transition-colors ${active(item.href) ? "text-brand dark:text-indigo-300" : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"}`}>
              {item.label}
              <span className={`absolute inset-x-3 -bottom-px h-0.5 origin-left rounded-full bg-gradient-to-r from-brand to-pulse transition-transform duration-300 ${active(item.href) ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100"}`} />
            </Link>
          ))}
          <Link href="/dashboard" className={`group relative px-3 py-2 text-sm font-medium no-underline ${pathname.startsWith("/dashboard") ? "text-brand" : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"}`}>
            Dashboard
            <span className="absolute inset-x-3 -bottom-px h-0.5 origin-left scale-x-0 rounded-full bg-gradient-to-r from-brand to-pulse transition-transform duration-300 group-hover:scale-x-100" />
          </Link>
        </nav>
        <div className="hidden items-center gap-2 lg:flex">
          <ThemeToggle />
          {user === undefined ? <div className="h-10 w-40" aria-hidden /> : user ? (
            <>
              <Link href="/settings" className="flex items-center gap-2 rounded-xl px-2 py-1.5 no-underline hover:bg-slate-100 dark:hover:bg-white/10" aria-label="Account settings">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand to-pulse text-sm font-bold text-white">{user.full_name.charAt(0).toUpperCase()}</span>
                <span className="max-w-[8rem] truncate text-sm font-medium">{user.full_name}</span>
              </Link>
              <button className="btn-secondary" onClick={logout}><LogOut className="h-4 w-4" /> Log out</button>
            </>
          ) : (
            <>
              <LinkButton href="/login" variant="secondary">Log in</LinkButton>
              <LinkButton href="/register" arrow>Register</LinkButton>
            </>
          )}
        </div>
        <div className="flex items-center gap-1 lg:hidden">
          <ThemeToggle />
          <button type="button" className="btn-ghost !px-2.5" aria-expanded={open} aria-controls="mobile-nav" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen(!open)}>
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      <div id="mobile-nav" className={`grid transition-[grid-template-rows] duration-300 lg:hidden ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`} {...(!open ? { inert: true } : {})}>
        <div className="overflow-hidden">
          <nav aria-label="Mobile" className="container-x flex flex-col gap-1 border-t border-slate-200/70 py-3 dark:border-white/10">
            {[...nav, { href: "/dashboard", label: "Dashboard" }].map((item) => (
              <Link key={item.href} href={item.href} aria-current={active(item.href) ? "page" : undefined}
                className={`rounded-xl px-3 py-3 text-base font-medium no-underline ${active(item.href) ? "bg-brand-soft text-brand dark:bg-brand/15 dark:text-indigo-200" : "hover:bg-slate-100 dark:hover:bg-white/10"}`}>
                {item.label}
              </Link>
            ))}
            <div className="mt-2 flex gap-2">
              {user ? (
                <>
                  <LinkButton href="/dashboard" className="flex-1"><LayoutDashboard className="h-4 w-4" /> Dashboard</LinkButton>
                  <button className="btn-secondary flex-1" onClick={logout}><LogOut className="h-4 w-4" /> Log out</button>
                </>
              ) : (
                <>
                  <LinkButton href="/login" variant="secondary" className="flex-1">Log in</LinkButton>
                  <LinkButton href="/register" className="flex-1">Register</LinkButton>
                </>
              )}
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}

const footerCols = [
  { title: "Product", links: [["/features", "Features"], ["/how-it-works", "How it works"], ["/dashboard", "Dashboard"]] },
  { title: "Project", links: [["/about", "About"], ["/contact", "Contact"]] },
  { title: "Legal", links: [["/privacy", "Privacy policy"], ["/terms", "Terms of use"]] },
  { title: "Account", links: [["/login", "Log in"], ["/register", "Register"]] },
];

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-slate-200/70 bg-white/60 dark:border-white/10 dark:bg-slate-950/40">
      <div className="container-x grid gap-10 py-12 md:grid-cols-[1.4fr_repeat(4,1fr)]">
        <div>
          <Brand />
          <p className="muted mt-3 max-w-xs">AI-assisted website monitoring, incident detection and evidence-based root cause analysis.</p>
        </div>
        {footerCols.map((col) => (
          <nav key={col.title} aria-label={col.title}>
            <h2 className="font-sans text-sm font-semibold">{col.title}</h2>
            <ul className="mt-3 space-y-2">
              {col.links.map(([href, label]) => (
                <li key={href}><Link href={href} className="text-sm text-slate-600 no-underline hover:text-brand dark:text-slate-400 dark:hover:text-white">{label}</Link></li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t border-slate-200/70 py-5 text-center text-xs text-slate-500 dark:border-white/10">College project. Not a commercial service.</div>
    </footer>
  );
}
