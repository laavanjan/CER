import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";

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
            <nav className="bg-white border-b border-gray-200 px-6 py-4">
              <div className="max-w-7xl mx-auto flex items-center gap-6">
                <a href="/" className="text-xl font-bold text-gray-900">
                  ethiksa-cer
                </a>
                <span className="text-sm text-gray-500 hidden sm:inline">AIGAP · Code Ethics Reviewer</span>
                <nav className="flex items-center gap-4 ml-auto text-sm font-medium">
                  <a href="/intake" className="text-gray-600 hover:text-indigo-600 transition-colors">
                    New Review
                  </a>
                  <a href="/controls" className="text-gray-600 hover:text-indigo-600 transition-colors">
                    Controls
                  </a>
                </nav>
              </div>
            </nav>
            <div className="max-w-7xl mx-auto px-6 py-8">{children}</div>
          </main>
        </Providers>
      </body>
    </html>
  );
}
