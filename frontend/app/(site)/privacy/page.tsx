import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacy policy" };

const sections: [string, string[]][] = [
  ["What the app stores", ["Account details: your name, email address and notification and theme preferences.", "Monitoring data: the websites you add, scan results, measurements, anomaly records, incidents, AI notes and reports.", "Agent tokens if you create a monitoring agent. A token is shown once when created."]],
  ["What stays in your browser", ["Your login session (access and refresh tokens) is kept in sessionStorage and is removed when you log out or close the tab.", "Your theme choice is kept in localStorage.", "The frontend does not set advertising or analytics cookies."]],
  ["Third-party services", ["Websites you add are checked by the backend. When a PageSpeed key is configured, the website URL is sent to Google PageSpeed Insights.", "When a Gemini key is configured, incident evidence may be sent to Google Gemini to produce an explanation.", "Data is hosted using the services the site owner configures, such as Supabase and Upstash."]],
  ["Your choices", ["You can delete a website, which removes its history.", "You can log out to revoke your session."]],
];

export default function PrivacyPage() {
  return (
    <div className="container-x max-w-3xl py-16">
      <h1 className="text-4xl font-bold">Privacy policy</h1>
      <p className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">Draft for owner review. This describes how the application behaves, not a legal guarantee. Review it before public deployment.</p>
      <div className="mt-8 space-y-8">
        {sections.map(([title, items]) => (
          <section key={title}><h2 className="text-xl font-bold">{title}</h2><ul className="muted mt-2 list-disc space-y-1.5 pl-5 text-base">{items.map((i) => <li key={i}>{i}</li>)}</ul></section>
        ))}
      </div>
    </div>
  );
}
