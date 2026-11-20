import type { Metadata } from "next";

export const metadata: Metadata = { title: "Terms of use" };

const terms = [
  "Only add websites you own or are permitted to monitor.",
  "Scans are non-intrusive, but you are responsible for the sites you add.",
  "Results, predictions and AI explanations are aids, not guarantees. Verify important findings yourself.",
  "Do not attempt to bypass the address restrictions or abuse the service.",
  "This is a college project provided as is, without warranty. Availability is not guaranteed.",
];

export default function TermsPage() {
  return (
    <div className="container-x max-w-3xl py-16">
      <h1 className="text-4xl font-bold">Terms of use</h1>
      <p className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">Draft for owner review before public deployment. Not legal advice.</p>
      <ol className="muted mt-8 list-decimal space-y-3 pl-5 text-base">{terms.map((t) => <li key={t}>{t}</li>)}</ol>
    </div>
  );
}
