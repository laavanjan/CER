import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";
import ErrorBoundary from "@/components/ErrorBoundary";

export const metadata: Metadata = {
  title: "ethiksa-cer | AI Ethics Code Reviewer",
  description: "AIGAP · Automated pipeline that scans AI system repositories against ethical controls",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <main className="min-h-screen bg-gray-50">

            {/* ── Top navigation bar ── */}
            <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-200/70 shadow-sm">
              <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center gap-4">

                {/* Brand */}
                <a href="/" className="flex items-center gap-2.5 group flex-shrink-0">
                  {/* Logo mark */}
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center shadow-sm group-hover:shadow-indigo-300 transition-shadow">
                    <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                    </svg>
                  </div>
                  {/* Name */}
                  <span className="text-[15px] font-bold text-gray-900 tracking-tight group-hover:text-indigo-700 transition-colors">
                    ethiksa<span className="text-indigo-600">-cer</span>
                  </span>
                </a>

                {/* Divider */}
                <div className="h-5 w-px bg-gray-200 flex-shrink-0" />

                {/* Subtitle */}
                <span className="hidden sm:inline-flex items-center gap-2 text-xs text-gray-400 font-medium tracking-wide">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-indigo-50 border border-indigo-100 text-indigo-500 text-[11px] font-semibold">
                    AIGAP
                  </span>
                  Code Ethics Reviewer
                </span>

                {/* Right nav */}
                <nav className="flex items-center gap-1 ml-auto">
                  <a
                    href="/info.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    {/* Info icon */}
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
                    </svg>
                    Info
                  </a>

                  <a
                    href="/intake"
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    {/* Plus icon */}
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                    New Review
                  </a>

                  <a
                    href="/controls"
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-gray-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg transition-colors"
                  >
                    {/* List icon */}
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 12h.007v.008H3.75V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm-.375 5.25h.007v.008H3.75v-.008zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                    </svg>
                    Controls
                  </a>

                  {/* CTA button */}
                  {/* <a
                    href="/intake"
                    className="ml-2 inline-flex items-center gap-1.5 px-4 py-1.5 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-sm font-semibold rounded-lg shadow-sm hover:shadow-md transition-all active:scale-95"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
                    </svg>
                    Run Scan
                  </a> */}
                </nav>

              </div>
            </header>

            {/* ── Page content ── */}
            <div className="max-w-[1600px] mx-auto px-6 py-8">
              <ErrorBoundary>{children}</ErrorBoundary>
            </div>

          </main>
        </Providers>
      </body>
    </html>
  );
}
