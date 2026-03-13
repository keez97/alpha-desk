import { useState, useEffect, useCallback } from 'react';
import { fetchMorningReport, fetchCustomReport } from '../../lib/api';

interface ReportSection {
  title: string;
  content: string;
}

const AVAILABLE_TOPICS = [
  { key: 'market_snapshot', label: 'Market Snapshot', default: true },
  { key: 'sector_rotation', label: 'Sector Rotation', default: true },
  { key: 'macro_pulse', label: 'Macro Pulse', default: true },
  { key: 'key_levels', label: 'Technical Levels', default: false },
  { key: 'volatility_regime', label: 'Volatility Regime', default: false },
  { key: 'market_breadth', label: 'Market Breadth', default: false },
  { key: 'earnings_preview', label: 'Earnings Preview', default: false },
  { key: 'week_ahead', label: 'Week Ahead', default: true },
];

function getInitialTopics(): Set<string> {
  try {
    const saved = localStorage.getItem('morning_report_topics');
    if (saved) return new Set(JSON.parse(saved));
  } catch {}
  return new Set(AVAILABLE_TOPICS.filter(t => t.default).map(t => t.key));
}

export function MarketReportPanel() {
  const [report, setReport] = useState<Record<string, ReportSection> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['market_snapshot']));
  const [selectedTopics, setSelectedTopics] = useState<Set<string>>(getInitialTopics);
  const [showTopicPicker, setShowTopicPicker] = useState(false);

  const loadReport = useCallback(async (topics: Set<string>) => {
    try {
      setLoading(true);
      setError(null);
      const topicArr = Array.from(topics);
      // Use default endpoint if only default topics selected, otherwise custom
      const defaults = new Set(AVAILABLE_TOPICS.filter(t => t.default).map(t => t.key));
      const isDefault = topicArr.length === defaults.size && topicArr.every(t => defaults.has(t));

      let data: Record<string, ReportSection>;
      if (isDefault) {
        data = await fetchMorningReport();
      } else {
        data = await fetchCustomReport(topicArr);
      }
      setReport(data);
    } catch (e: any) {
      setError(e.message || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport(selectedTopics);
  }, []); // Only load on mount

  const toggleTopic = (key: string) => {
    setSelectedTopics(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key); // Keep at least 1
      } else {
        next.add(key);
      }
      try { localStorage.setItem('morning_report_topics', JSON.stringify(Array.from(next))); } catch {}
      return next;
    });
  };

  const applyTopics = () => {
    setShowTopicPicker(false);
    loadReport(selectedTopics);
  };

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
            <span className="text-xs text-neutral-500 ml-2">Analyzing market conditions...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-neutral-800 rounded px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-neutral-500">Morning Report temporarily unavailable</span>
          <button
            onClick={() => loadReport(selectedTopics)}
            className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors px-2 py-1 border border-neutral-700 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!report) return null;

  const sectionKeys = Array.from(selectedTopics);

  return (
    <div className="border border-neutral-800 rounded overflow-hidden">
      <div className="px-4 py-2 border-b border-neutral-800 flex items-center justify-between">
        <span className="text-xs font-medium text-neutral-300">Morning Report</span>
        <button
          onClick={() => setShowTopicPicker(!showTopicPicker)}
          className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors flex items-center gap-1"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Configure Topics
        </button>
      </div>

      {/* Topic picker */}
      {showTopicPicker && (
        <div className="px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
          <span className="text-xs text-neutral-500 block mb-2">Select topics to include:</span>
          <div className="flex flex-wrap gap-1.5 mb-2">
            {AVAILABLE_TOPICS.map(topic => {
              const isSelected = selectedTopics.has(topic.key);
              return (
                <button
                  key={topic.key}
                  onClick={() => toggleTopic(topic.key)}
                  className={`px-2 py-1 rounded text-xs font-medium transition-colors border ${
                    isSelected
                      ? 'border-neutral-600 bg-neutral-800 text-neutral-200'
                      : 'border-neutral-800 text-neutral-500 hover:border-neutral-700 hover:text-neutral-400'
                  }`}
                >
                  {isSelected && <span className="mr-1">&#10003;</span>}
                  {topic.label}
                </button>
              );
            })}
          </div>
          <button
            onClick={applyTopics}
            className="px-3 py-1 rounded text-xs font-medium bg-neutral-700 text-neutral-200 hover:bg-neutral-600 transition-colors"
          >
            Apply
          </button>
        </div>
      )}

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
                  className={`w-3 h-3 text-neutral-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
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
