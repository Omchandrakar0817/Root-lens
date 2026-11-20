import { SiteFooter, SiteHeader } from "@/components/SiteChrome";
import { LinkButton } from "@/components/ui";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="container-x flex min-h-[60vh] flex-col items-center justify-center py-20 text-center">
        <p className="font-display text-7xl font-bold text-brand">404</p>
        <h1 className="mt-3 text-2xl font-bold">This page does not exist</h1>
        <p className="muted mt-2 max-w-md">The link may be broken or the page may have moved.</p>
        <div className="mt-6 flex gap-3"><LinkButton href="/" arrow>Back to home</LinkButton><LinkButton href="/dashboard" variant="secondary">Dashboard</LinkButton></div>
      </main>
      <SiteFooter />
    </>
  );
}
