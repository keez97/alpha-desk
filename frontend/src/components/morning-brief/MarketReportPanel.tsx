import { useState, useEffect } from 'react';
import { fetchMorningReport } from '../../lib/api';

interface ReportSection {
  title: string;
  content: string;
}

export function MarketReportPanel() {
  const [report, setReport] = useState<Record<string, ReportSection> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['market_snapshot']));

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchMorningReport();
        if (!cancelled) {
          setReport(data);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e.message || 'Failed to generate report');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const toggleSection = (key: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="border border-neutral-800 rounded p-4">
        <div className="flex items-center gap-3">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-neutral-700 border-t-neutral-400" />
          <div>
            <span className="text-xs text-neutral-400">Generating Morning Report</span>
            <span className="text-[10px] text-neutral-600 ml-2">Analyzing market conditions...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-neutral-800 rounded px-4 py-3">
        <span className="text-xs text-red-400/80">Report unavailable: {error}</span>
      </div>
    );
  }

  if (!report) return null;

  const sectionKeys = ['market_snapshot', 'sector_rotation', 'macro_pulse', 'week_ahead'];

  return (
    <div className="border border-neutral-800 rounded overflow-hidden">
      <div className="px-4 py-2 border-b border-neutral-800 flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">Morning Report</span>
        <span className="text-[10px] text-neutral-600">Auto-generated</span>
      </div>

      <div className="divide-y divide-neutral-800/50">
        {sectionKeys.map(key => {
          const section = report[key];
          if (!section) return null;
          const isExpanded = expandedSections.has(key);

          return (
            <div key={key}>
              <button
                onClick={() => toggleSection(key)}
                className="flex w-full items-center justify-between px-4 py-2 hover:bg-neutral-900/50 transition-colors"
              >
                <span className="text-xs font-medium text-neutral-300">{section.title}</span>
                <svg
                  className={`w-3 h-3 text-neutral-600 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {isExpanded && (
                <div className="px-4 pb-3 pt-0">
                  <p className="text-xs text-neutral-400 leading-relaxed whitespace-pre-line">
                    {section.content}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
