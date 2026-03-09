import { useState } from 'react';
import { GradeBadge } from '../shared/GradeBadge';
import type { Grade } from '../../lib/api';

interface StockGraderCardProps {
  ticker: string;
  grade: Grade;
}

export function StockGraderCard({ ticker, grade }: StockGraderCardProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('summary');

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-6">
        <div className="mb-6 text-center">
          <h2 className="mb-4 text-2xl font-bold text-white">{ticker}</h2>
          <GradeBadge grade={grade.overall} size="lg" />
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
          {grade.metrics.map((metric) => (
            <div key={metric.name} className="text-center">
              <GradeBadge grade={metric.grade} size="sm" />
              <p className="mt-2 text-xs text-gray-400">{metric.name}</p>
              <p className="font-mono text-sm text-gray-300">{metric.value.toFixed(2)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Summary Section */}
      <div className="rounded-lg border border-gray-700 bg-gray-800/30">
        <button
          onClick={() => setExpandedSection(expandedSection === 'summary' ? null : 'summary')}
          className="flex w-full items-center justify-between px-6 py-4 hover:bg-gray-700/20 transition-colors"
        >
          <h3 className="font-semibold text-white">Summary</h3>
          <span className="text-gray-400">{expandedSection === 'summary' ? '−' : '+'}</span>
        </button>
        {expandedSection === 'summary' && (
          <div className="border-t border-gray-700 px-6 py-4">
            <p className="text-sm text-gray-300">{grade.summary}</p>
          </div>
        )}
      </div>

      {/* Risks Section */}
      <div className="rounded-lg border border-gray-700 bg-gray-800/30">
        <button
          onClick={() => setExpandedSection(expandedSection === 'risks' ? null : 'risks')}
          className="flex w-full items-center justify-between px-6 py-4 hover:bg-gray-700/20 transition-colors"
        >
          <h3 className="font-semibold text-white">Risks</h3>
          <span className="text-gray-400">{expandedSection === 'risks' ? '−' : '+'}</span>
        </button>
        {expandedSection === 'risks' && (
          <div className="border-t border-gray-700 px-6 py-4">
            <ul className="space-y-2">
              {grade.risks.map((risk, idx) => (
                <li key={idx} className="flex space-x-2 text-sm text-gray-300">
                  <span className="text-red-400">•</span>
                  <span>{risk}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Catalysts Section */}
      <div className="rounded-lg border border-gray-700 bg-gray-800/30">
        <button
          onClick={() => setExpandedSection(expandedSection === 'catalysts' ? null : 'catalysts')}
          className="flex w-full items-center justify-between px-6 py-4 hover:bg-gray-700/20 transition-colors"
        >
          <h3 className="font-semibold text-white">Catalysts</h3>
          <span className="text-gray-400">{expandedSection === 'catalysts' ? '−' : '+'}</span>
        </button>
        {expandedSection === 'catalysts' && (
          <div className="border-t border-gray-700 px-6 py-4">
            <ul className="space-y-2">
              {grade.catalysts.map((catalyst, idx) => (
                <li key={idx} className="flex space-x-2 text-sm text-gray-300">
                  <span className="text-green-400">•</span>
                  <span>{catalyst}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
