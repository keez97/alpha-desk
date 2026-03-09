import { useState } from 'react';
import { GradeBadge } from '../shared/GradeBadge';
import type { Grade } from '../../lib/api';

interface StockGraderCardProps {
  ticker: string;
  grade: Grade;
}

// Simple radar chart using SVG
function RadarChart({ dimensions }: { dimensions: Grade['dimensions'] }) {
  if (!dimensions || dimensions.length === 0) return null;

  const size = 220;
  const center = size / 2;
  const radius = 85;
  const levels = 5;

  const angleStep = (2 * Math.PI) / dimensions.length;

  // Draw concentric pentagons/polygons for grid
  const gridPaths = [];
  for (let l = 1; l <= levels; l++) {
    const r = (l / levels) * radius;
    const points = dimensions.map((_, i) => {
      const angle = i * angleStep - Math.PI / 2;
      return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
    }).join(' ');
    gridPaths.push(
      <polygon
        key={l}
        points={points}
        fill="none"
        stroke="rgba(255,255,255,0.08)"
        strokeWidth={1}
      />
    );
  }

  // Axis lines
  const axisLines = dimensions.map((_, i) => {
    const angle = i * angleStep - Math.PI / 2;
    return (
      <line
        key={i}
        x1={center}
        y1={center}
        x2={center + radius * Math.cos(angle)}
        y2={center + radius * Math.sin(angle)}
        stroke="rgba(255,255,255,0.08)"
        strokeWidth={1}
      />
    );
  });

  // Data polygon
  const dataPoints = dimensions.map((dim, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const r = (dim.score / 10) * radius;
    return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
  }).join(' ');

  // Labels
  const labels = dimensions.map((dim, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const labelR = radius + 20;
    const x = center + labelR * Math.cos(angle);
    const y = center + labelR * Math.sin(angle);
    return (
      <text
        key={i}
        x={x}
        y={y}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#9ca3af"
        fontSize={9}
        fontFamily="Inter, system-ui, sans-serif"
      >
        {dim.name}
      </text>
    );
  });

  // Score dots
  const dots = dimensions.map((dim, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const r = (dim.score / 10) * radius;
    return (
      <circle
        key={i}
        cx={center + r * Math.cos(angle)}
        cy={center + r * Math.sin(angle)}
        r={3}
        fill="#3b82f6"
        stroke="#fff"
        strokeWidth={1}
      />
    );
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
      {gridPaths}
      {axisLines}
      <polygon
        points={dataPoints}
        fill="rgba(59, 130, 246, 0.15)"
        stroke="#3b82f6"
        strokeWidth={2}
      />
      {dots}
      {labels}
    </svg>
  );
}

function ScenarioTable({ scenarios }: { scenarios: Grade['scenarios'] }) {
  if (!scenarios) return null;

  const rows = [
    { label: 'Bull', data: scenarios.bull, color: 'text-green-400', bg: 'bg-green-900/20' },
    { label: 'Base', data: scenarios.base, color: 'text-gray-300', bg: 'bg-gray-700/20' },
    { label: 'Bear', data: scenarios.bear, color: 'text-red-400', bg: 'bg-red-900/20' },
  ];

  return (
    <div className="space-y-2">
      {rows.map(({ label, data, color, bg }) => (
        <div key={label} className={`rounded-md ${bg} px-4 py-3`}>
          <div className="flex items-center justify-between mb-1">
            <span className={`text-sm font-semibold ${color}`}>{label} Case</span>
            <div className="flex items-center gap-3">
              <span className={`text-sm font-mono ${color}`}>
                {(data.target_pct > 0 ? '+' : '')}{data.target_pct.toFixed(0)}%
              </span>
              <span className="text-xs text-gray-500">
                {(data.probability * 100).toFixed(0)}% prob
              </span>
            </div>
          </div>
          <ul className="space-y-0.5">
            {data.drivers.map((d: string, i: number) => (
              <li key={i} className="text-xs text-gray-400">• {d}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function StockGraderCard({ ticker, grade }: StockGraderCardProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>('dimensions');

  const toggle = (key: string) => setExpandedSection(prev => prev === key ? null : key);

  const compositeScore = grade.compositeScore ?? 0;
  const regime = grade.regime || 'neutral';

  return (
    <div className="space-y-3">
      {/* Header with score and grade */}
      <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white">{ticker}</h2>
            <p className="text-xs text-gray-500 mt-1">
              {grade.sector} · Regime: <span className="capitalize">{regime.replace('_', ' ')}</span>
            </p>
          </div>
          <div className="text-right">
            <GradeBadge grade={grade.overall} size="lg" />
            <p className="text-xs text-gray-500 mt-1">
              Score: {compositeScore.toFixed(1)}/10
            </p>
          </div>
        </div>

        {/* Radar chart */}
        <RadarChart dimensions={grade.dimensions} />

        {/* Dimension scores row */}
        <div className="grid grid-cols-4 gap-2 mt-4">
          {grade.dimensions.map(dim => (
            <div key={dim.name} className="text-center">
              <div className="text-lg font-mono font-bold text-white">{dim.score.toFixed(1)}</div>
              <div className="text-[10px] text-gray-400 leading-tight">{dim.name}</div>
              <div className="text-[10px] text-gray-600">{(dim.weight * 100).toFixed(0)}%</div>
            </div>
          ))}
        </div>
      </div>

      {/* Thesis */}
      <div className="rounded-lg border border-gray-700 bg-gray-800/30 px-5 py-4">
        <p className="text-sm text-gray-300 leading-relaxed">{grade.summary}</p>
      </div>

      {/* Scenarios */}
      {grade.scenarios && (
        <div className="rounded-lg border border-gray-700 bg-gray-800/30">
          <button
            onClick={() => toggle('scenarios')}
            className="flex w-full items-center justify-between px-5 py-3 hover:bg-gray-700/20 transition-colors"
          >
            <h3 className="text-sm font-semibold text-white">Scenario Analysis</h3>
            <span className="text-gray-400 text-sm">{expandedSection === 'scenarios' ? '−' : '+'}</span>
          </button>
          {expandedSection === 'scenarios' && (
            <div className="border-t border-gray-700 px-5 py-4">
              <ScenarioTable scenarios={grade.scenarios} />
            </div>
          )}
        </div>
      )}

      {/* Dimension Details */}
      <div className="rounded-lg border border-gray-700 bg-gray-800/30">
        <button
          onClick={() => toggle('dimensions')}
          className="flex w-full items-center justify-between px-5 py-3 hover:bg-gray-700/20 transition-colors"
        >
          <h3 className="text-sm font-semibold text-white">Dimension Breakdown</h3>
          <span className="text-gray-400 text-sm">{expandedSection === 'dimensions' ? '−' : '+'}</span>
        </button>
        {expandedSection === 'dimensions' && (
          <div className="border-t border-gray-700 divide-y divide-gray-700/50">
            {grade.dimensions.map(dim => (
              <div key={dim.name} className="px-5 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">{dim.name}</span>
                  <span className="text-sm font-mono text-blue-400">{dim.score.toFixed(1)}</span>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed">{dim.assessment}</p>
                {dim.data_points && dim.data_points.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {dim.data_points.map((dp: string, i: number) => (
                      <span key={i} className="text-[10px] bg-gray-700/50 text-gray-300 px-2 py-0.5 rounded">
                        {dp}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Catalysts */}
      {grade.catalystEvents && grade.catalystEvents.length > 0 && (
        <div className="rounded-lg border border-gray-700 bg-gray-800/30">
          <button
            onClick={() => toggle('catalysts')}
            className="flex w-full items-center justify-between px-5 py-3 hover:bg-gray-700/20 transition-colors"
          >
            <h3 className="text-sm font-semibold text-white">Catalyst Pipeline</h3>
            <span className="text-gray-400 text-sm">{expandedSection === 'catalysts' ? '−' : '+'}</span>
          </button>
          {expandedSection === 'catalysts' && (
            <div className="border-t border-gray-700 px-5 py-4">
              <div className="space-y-2">
                {grade.catalystEvents.map((cat, i) => (
                  <div key={i} className="flex items-start gap-3 text-sm">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      cat.impact === 'positive' ? 'bg-green-900/30 text-green-400' :
                      cat.impact === 'negative' ? 'bg-red-900/30 text-red-400' :
                      'bg-gray-700/30 text-gray-400'
                    }`}>
                      {cat.impact}
                    </span>
                    <div className="flex-1">
                      <span className="text-gray-300">{cat.event}</span>
                      <span className="text-gray-500 text-xs ml-2">
                        {cat.expected_date} · {(cat.probability * 100).toFixed(0)}% prob
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Risks */}
      {grade.risks.length > 0 && (
        <div className="rounded-lg border border-gray-700 bg-gray-800/30">
          <button
            onClick={() => toggle('risks')}
            className="flex w-full items-center justify-between px-5 py-3 hover:bg-gray-700/20 transition-colors"
          >
            <h3 className="text-sm font-semibold text-white">Key Risks</h3>
            <span className="text-gray-400 text-sm">{expandedSection === 'risks' ? '−' : '+'}</span>
          </button>
          {expandedSection === 'risks' && (
            <div className="border-t border-gray-700 px-5 py-4">
              <ul className="space-y-1.5">
                {grade.risks.map((risk, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-300">
                    <span className="text-red-400 mt-0.5">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Contrarian Signal */}
      {grade.contrarianSignal && (
        <div className="rounded-lg border border-amber-700/40 bg-amber-900/10 px-5 py-4">
          <div className="flex items-start gap-2">
            <span className="text-amber-400 text-sm mt-0.5">⚡</span>
            <div>
              <h4 className="text-sm font-semibold text-amber-300 mb-1">Contrarian Signal</h4>
              <p className="text-sm text-gray-300">{grade.contrarianSignal}</p>
            </div>
          </div>
        </div>
      )}

      {/* Data Gaps */}
      {grade.dataGaps && grade.dataGaps.length > 0 && (
        <div className="rounded-lg border border-gray-700/50 bg-gray-800/20 px-5 py-3">
          <p className="text-xs text-gray-500">
            <span className="font-medium">Data gaps: </span>
            {grade.dataGaps.join(' · ')}
          </p>
        </div>
      )}
    </div>
  );
}
