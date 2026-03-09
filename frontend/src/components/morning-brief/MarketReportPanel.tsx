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
      <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-6">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <div>
            <h3 className="text-sm font-semibold text-white">Generating Morning Report</h3>
            <p className="text-xs text-gray-400">AI is analyzing current market conditions...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-800/50 bg-red-900/10 p-4">
        <p className="text-sm text-red-400">Report unavailable: {error}</p>
      </div>
    );
  }

  if (!report) return null;

  const sectionKeys = ['market_snapshot', 'sector_rotation', 'macro_pulse', 'week_ahead'];
  const sectionIcons: Record<string, string> = {
    market_snapshot: '📊',
    sector_rotation: '🔄',
    macro_pulse: '📈',
    week_ahead: '📅',
  };

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/30 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Morning Market Report</h3>
        <span className="text-xs text-gray-500">Auto-generated</span>
      </div>

      <div className="divide-y divide-gray-700/50">
        {sectionKeys.map(key => {
          const section = report[key];
          if (!section) return null;
          const isExpanded = expandedSections.has(key);
          const icon = sectionIcons[key] || '📋';

          return (
            <div key={key}>
              <button
                onClick={() => toggleSection(key)}
                className="flex w-full items-center justify-between px-4 py-3 hover:bg-gray-700/20 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <span className="text-sm">{icon}</span>
                  <span className="text-sm font-medium text-white">{section.title}</span>
                </span>
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {isExpanded && (
                <div className="px-4 pb-4 pt-0">
                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">
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
