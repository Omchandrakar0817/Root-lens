"use client";

import { Mail } from "lucide-react";
import { FormEvent, useState } from "react";
import { Button, Empty } from "@/components/ui";

const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL || "";

export default function ContactPage() {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [opened, setOpened] = useState(false);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const name = String(data.get("name") || "").trim();
    const email = String(data.get("email") || "").trim();
    const message = String(data.get("message") || "").trim();
    const next: Record<string, string> = {};
    if (name.length < 2) next.name = "Enter your name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = "Enter a valid email address.";
    if (message.length < 10) next.message = "Write at least 10 characters.";
    setErrors(next);
    setOpened(false);
    if (Object.keys(next).length) return;
    const body = `${message}\n\nFrom: ${name} <${email}>`;
    window.location.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(`Incident RCA message from ${name}`)}&body=${encodeURIComponent(body)}`;
    setOpened(true);
  }

  const field = (id: string) => ({ "aria-invalid": errors[id] ? true : undefined, "aria-describedby": errors[id] ? `${id}-err` : undefined });
  const err = (id: string) => errors[id] && <p id={`${id}-err`} role="alert" className="mt-1 text-sm text-red-600 dark:text-red-400">{errors[id]}</p>;

  return (
    <div className="container-x max-w-2xl py-16">
      <h1 className="text-4xl font-bold">Contact</h1>
      <p className="muted mt-3 text-base">Questions about the project or feedback on the app.</p>
      <div className="mt-8">
        {!CONTACT_EMAIL ? (
          <Empty icon={<Mail className="h-6 w-6" />} title="Contact is not configured yet" body="The site owner has not set a contact address. Set NEXT_PUBLIC_CONTACT_EMAIL in the frontend environment to enable this form." />
        ) : (
          <form className="card space-y-4" onSubmit={onSubmit} noValidate>
            <div><label className="label" htmlFor="name">Name</label><input id="name" name="name" className="input" autoComplete="name" {...field("name")} />{err("name")}</div>
            <div><label className="label" htmlFor="email">Your email</label><input id="email" name="email" type="email" className="input" autoComplete="email" {...field("email")} />{err("email")}</div>
            <div><label className="label" htmlFor="message">Message</label><textarea id="message" name="message" rows={5} className="input" {...field("message")} />{err("message")}</div>
            <Button type="submit" arrow>Open in email app</Button>
            {opened && <p role="status" className="muted">Your email app should have opened with the message filled in. Nothing is sent until you send it from there.</p>}
          </form>
        )}
      </div>
    </div>
  );
}
