import { Activity, BarChart3, BrainCircuit, CalendarClock, FileClock, Gauge, GitBranch, LockKeyhole, SearchCheck, ShieldCheck, type LucideIcon } from "lucide-react";

export type Feature = { icon: LucideIcon; title: string; short: string; detail: string };

export const features: Feature[] = [
  { icon: Activity, title: "Website monitoring", short: "HTTP status, response time, DNS and timeouts for any public URL.", detail: "Each check records the HTTP status, response time and error type. A single failed check stays “unknown” until a second check confirms it, which keeps one-off network blips from raising false alarms." },
  { icon: BrainCircuit, title: "AI-assisted incident prediction", short: "Rules during cold start, then Isolation Forest on your own history.", detail: "Early checks use simple statistical rules. Once a site has enough samples, an Isolation Forest model is trained on that site’s own measurements. Every result shows whether a model was actually trained." },
  { icon: GitBranch, title: "Root cause analysis", short: "Ranked hypotheses, kept separate from confirmed facts.", detail: "Each incident stores ranked explanations with the evidence behind them. A cause is marked confirmed only when a measurement directly shows it, such as repeated DNS failure. Everything else stays a hypothesis." },
  { icon: CalendarClock, title: "Scheduled scanning", short: "Run checks on an interval without opening the app.", detail: "Start, pause or stop monitoring per website and choose the interval. Scheduled runs are executed by the backend worker and scheduler, so they need Redis and the worker process to be running." },
  { icon: Gauge, title: "Performance monitoring", short: "Google PageSpeed scores and Core Web Vitals per device type.", detail: "When a PageSpeed API key is configured on the server, scans store performance, accessibility, SEO and best-practice scores plus LCP, CLS, INP, FCP and TBT. Missing values are shown as missing, not guessed." },
  { icon: ShieldCheck, title: "SSL certificate monitoring", short: "HTTPS availability, certificate validity and days to expiry.", detail: "Scans check whether HTTPS is available, whether the certificate is valid and how many days remain before it expires." },
  { icon: LockKeyhole, title: "Security header analysis", short: "Non-intrusive review of response headers and configuration.", detail: "The analysis reads the headers a site already returns and lists findings with a severity. It does not probe or attack the target." },
  { icon: SearchCheck, title: "SEO and accessibility insights", short: "Title, metadata and accessibility findings from each scan.", detail: "Findings from the page content and from PageSpeed (when configured) are listed with severity so you can fix the most important items first." },
  { icon: BarChart3, title: "Analytics dashboard", short: "Charts built only from measurements stored in the database.", detail: "Response-time trends, anomaly scores and linear forecasts are drawn from stored data. When there is no data yet, the dashboard says so instead of filling in numbers." },
  { icon: FileClock, title: "Incident history and reports", short: "Acknowledge, resolve and reopen incidents; export reports.", detail: "Incidents keep a timeline of events. Reports summarize websites and incidents already in the database and can be downloaded as JSON." },
];

export const steps = [
  { title: "Add a website", body: "Enter a public HTTP or HTTPS address. Private, loopback and cloud-metadata addresses are rejected by the backend." },
  { title: "Configure monitoring", body: "Choose how often the site should be checked, and start, pause or stop scheduled monitoring at any time." },
  { title: "Collect metrics", body: "Each scan stores availability, response time, TLS, security-header, SEO and (if configured) PageSpeed results." },
  { title: "Detect anomalies", body: "Rules apply while history is short. With enough samples an Isolation Forest model learns what is normal for that site." },
  { title: "Analyze incidents", body: "A confirmed problem opens an incident with symptoms, evidence, a timeline and ranked root-cause hypotheses." },
  { title: "View results", body: "Read the explanation, follow verification steps, resolve the incident and export a report." },
];

export const benefits = [
  { title: "Fewer false alarms", body: "Failures are confirmed by a second check before a site is marked as having issues." },
  { title: "Honest evidence", body: "Confirmed facts and hypotheses are labeled separately, so you know what a measurement proves." },
  { title: "Works without an API key", body: "If Gemini is unavailable, a rule-based explanation is generated and labeled as such." },
  { title: "Safe by design", body: "Only public addresses are accepted and scans stay non-intrusive." },
];
