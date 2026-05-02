import Link from "next/link";

export default function HomePage() {
  return (
    <div className="max-w-2xl mx-auto text-center py-16">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">
        AI Ethics Code Reviewer
      </h1>
      <p className="text-lg text-gray-600 mb-8">
        Automated pipeline that scans AI system repositories against 78 ethical
        controls across 11 pillars, producing structured findings and remediation guidance.
      </p>
      <div className="flex gap-4 justify-center">
        <a
          href="/info.html"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center px-6 py-3 bg-gray-100 text-gray-800 font-medium rounded-lg hover:bg-gray-200 transition-colors border border-gray-300"
        >
          Info
        </a>
        <Link
          href="/intake"
          className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Start Review →
        </Link>
      </div>
    </div>
  );
}
