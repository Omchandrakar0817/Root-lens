import type { Metadata } from "next";
import { ToastProvider } from "@/components/ui";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Incident RCA — AI website monitoring and root cause analysis", template: "%s · Incident RCA" },
  description: "AI-based incident prediction and root cause analysis for application monitoring.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning data-scroll-behavior="smooth">
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{if(localStorage.getItem("theme")==="dark"||(!localStorage.getItem("theme")&&matchMedia("(prefers-color-scheme: dark)").matches)){document.documentElement.classList.add("dark")}}catch(e){}`,
          }}
        />
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[200] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-brand">Skip to content</a>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
