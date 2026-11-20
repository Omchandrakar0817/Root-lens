"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { LogoMark } from "./Brand";
import { Button } from "./ui";
import { api, loadSession, saveSession, type Session } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const register = mode === "register";
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [pending, setPending] = useState(false);

  useEffect(() => { if (loadSession()) router.replace("/dashboard"); }, [router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const full_name = String(data.get("full_name") || "").trim();
    const email = String(data.get("email") || "").trim();
    const password = String(data.get("password") || "");
    const errs: Record<string, string> = {};
    if (register && full_name.length < 2) errs.full_name = "Enter your name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = "Enter a valid email address.";
    if (!password || (register && password.length < 8)) errs.password = register ? "Use at least 8 characters." : "Enter your password.";
    setFieldErrors(errs);
    setError("");
    if (Object.keys(errs).length) return;
    setPending(true);
    try {
      const session = await api<Session>(register ? "/auth/register" : "/auth/login", { method: "POST", body: JSON.stringify(register ? { full_name, email, password } : { email, password }) });
      saveSession(session);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : register ? "Registration failed" : "Login failed");
      setPending(false);
    }
  }

  const fe = (id: string) => fieldErrors[id] && <p id={`${id}-err`} role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{fieldErrors[id]}</p>;
  const aria = (id: string) => ({ "aria-invalid": fieldErrors[id] ? true : undefined, "aria-describedby": fieldErrors[id] ? `${id}-err` : undefined });

  return (
    <div className="container-x flex max-w-md flex-col py-14">
      <LogoMark className="h-10 w-10" />
      <h1 className="mt-4 text-3xl font-bold">{register ? "Create your account" : "Welcome back"}</h1>
      <p className="muted mt-1">{register ? "Start monitoring your first website." : "Log in to see your monitoring dashboard."}</p>
      <form className="card mt-6 space-y-4" onSubmit={onSubmit} noValidate>
        {register && <div><label className="label" htmlFor="full_name">Name</label><input id="full_name" name="full_name" className="input" autoComplete="name" {...aria("full_name")} />{fe("full_name")}</div>}
        <div><label className="label" htmlFor="email">Email</label><input id="email" name="email" type="email" className="input" autoComplete="email" {...aria("email")} />{fe("email")}</div>
        <div><label className="label" htmlFor="password">Password</label><input id="password" name="password" type="password" className="input" autoComplete={register ? "new-password" : "current-password"} {...aria("password")} />{fe("password")}</div>
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{error}</p>}
        <Button type="submit" loading={pending} arrow className="w-full">{pending ? (register ? "Creating account…" : "Signing in…") : register ? "Create account" : "Sign in"}</Button>
      </form>
      <p className="muted mt-4">
        {register ? <>Already registered? <Link href="/login" className="font-semibold text-brand">Log in</Link></> : <>New here? <Link href="/register" className="font-semibold text-brand">Create an account</Link></>}
      </p>
    </div>
  );
}
