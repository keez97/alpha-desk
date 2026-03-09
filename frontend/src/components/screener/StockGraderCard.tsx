import { useState } from 'react';
import { GradeBadge } from '../shared/GradeBadge';
import type { Grade } from '../../lib/api';

interface StockGraderCardProps {
  ticker: string;
  grade: Grade;
}

function RadarChart({ dimensions }: { dimensions: Grade['dimensions'] }) {
  if (!dimensions || dimensions.length === 0) return null;

  const size = 200;
  const center = size / 2;
  const radius = 75;
  const levels = 5;
  const angleStep = (2 * Math.PI) / dimensions.length;

  const gridPaths = [];
  for (let l = 1; l <= levels; l++) {
    const r = (l / levels) * radius;
    const points = dimensions.map((_, i) => {
      const angle = i * angleStep - Math.PI / 2;
      return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
    }).join(' ');
    gridPaths.push(
      <polygon key={l} points={points} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
    );
  }

  const axisLines = dimensions.map((_, i) => {
    const angle = i * angleStep - Math.PI / 2;
    return (
      <line key={i} x1={center} y1={center} x2={center + radius * Math.cos(angle)} y2={center + radius * Math.sin(angle)} stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
    );
  });

  const dataPoints = dimensions.map((dim, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const r = (dim.score / 10) * radius;
    return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`;
  }).join(' ');

  const labels = dimensions.map((dim, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const labelR = radius + 18;
    return (
      <text key={i} x={center + labelR * Math.cos(angle)} y={center + labelR * Math.sin(angle)} textAnchor="middle" dominantBaseline="middle" fill="#525252" fontSize={8} fontFamily="Inter, system-ui, sans-serif">
        {dim.name}
      </text>
    );
  });

  const dots = dimensions.map((dim, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const r = (dim.score / 10) * radius;
    return (
      <circle key={i} cx={center + r * Math.cos(angle)} cy={center + r * Math.sin(angle)} r={2.5} fill="#a3a3a3" stroke="#000" strokeWidth={1} />
    );
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
      {gridPaths}
      {axisLines}
      <polygon points={dataPoints} fill="rgba(163, 163, 163, 0.08)" stroke="#525252" strokeWidth={1.5} />
      {dots}
      {labels}
    </svg>
  );
}

function ScenarioTable({ scenarios }: { scenarios: Grade['scenarios'] }) {
  if (!scenarios) return null;

  const rows = [
    { label: 'Bull', data: scenarios.bull, color: 'text-emerald-400', bg: 'bg-emerald-950/30' },
    { label: 'Base', data: scenarios.base, color: 'text-neutral-300', bg: 'bg-neutral-900/30' },
    { label: 'Bear', data: scenarios.bear, color: 'text-red-400', bg: 'bg-red-950/30' },
  ];

  return (
    <div className="space-y-1.5">
      {rows.map(({ label, data, color, bg }) => (
        <div key={label} className={`rounded ${bg} px-3 py-2`}>
          <div className="flex items-center justify-between mb-1">
            <span className={`text-xs font-medium ${color}`}>{label}</span>
            <div className="flex items-center gap-2">
              <span className={`text-xs font-mono ${color}`}>
                {(data.target_pct > 0 ? '+' : '')}{data.target_pct.toFixed(0)}%
              </span>
              <span className="text-[10px] text-neutral-600">
                {(data.probability * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <ul className="space-y-0.5">
            {data.drivers.map((d: string, i: number) => (
              <li key={i} className="text-[11px] text-neutral-500">• {d}</li>
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
    <div className="space-y-2">
      {/* Header */}
      <div className="border border-neutral-800 rounded p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <span className="text-lg font-bold text-neutral-100">{ticker}</span>
            <span className="text-[10px] text-neutral-600 ml-2">
              {grade.sector} · {regime.replace('_', ' ')}
            </span>
          </div>
          <div className="text-right flex items-center gap-3">
            <span className="text-xs font-mono text-neutral-400">{compositeScore.toFixed(1)}/10</span>
            <GradeBadge grade={grade.overall} size="lg" />
          </div>
        </div>

        <RadarChart dimensions={grade.dimensions} />

        <div className="grid grid-cols-4 gap-1.5 mt-3">
          {grade.dimensions.map(dim => (
            <div key={dim.name} className="text-center">
              <div className="text-sm font-mono font-medium text-neutral-200">{dim.score.toFixed(1)}</div>
              <div className="text-[9px] text-neutral-500 leading-tight">{dim.name}</div>
              <div className="text-[9px] text-neutral-700">{(dim.weight * 100).toFixed(0)}%</div>
            </div>
          ))}
        </div>
      </div>

      {/* Thesis */}
      <div className="border border-neutral-800 rounded px-4 py-3">
        <p className="text-xs text-neutral-400 leading-relaxed">{grade.summary}</p>
      </div>

      {/* Scenarios */}
      {grade.scenarios && (
        <div className="border border-neutral-800 rounded">
          <button onClick={() => toggle('scenarios')} className="flex w-full items-center justify-between px-4 py-2 hover:bg-neutral-900/50 transition-colors">
            <span className="text-xs font-medium text-neutral-300">Scenarios</span>
            <span className="text-neutral-600 text-xs">{expandedSection === 'scenarios' ? '−' : '+'}</span>
          </button>
          {expandedSection === 'scenarios' && (
            <div className="border-t border-neutral-800 px-4 py-3">
              <ScenarioTable scenarios={grade.scenarios} />
            </div>
          )}
        </div>
      )}

      {/* Dimensions */}
      <div className="border border-neutral-800 rounded">
        <button onClick={() => toggle('dimensions')} className="flex w-full items-center justify-between px-4 py-2 hover:bg-neutral-900/50 transition-colors">
          <span className="text-xs font-medium text-neutral-300">Dimensions</span>
          <span className="text-neutral-600 text-xs">{expandedSection === 'dimensions' ? '−' : '+'}</span>
        </button>
        {expandedSection === 'dimensions' && (
          <div className="border-t border-neutral-800 divide-y divide-neutral-900">
            {grade.dimensions.map(dim => (
              <div key={dim.name} className="px-4 py-2">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-xs font-medium text-neutral-300">{dim.name}</span>
                  <span className="text-xs font-mono text-neutral-400">{dim.score.toFixed(1)}</span>
                </div>
                <p className="text-[11px] text-neutral-500 leading-relaxed">{dim.assessment}</p>
                {dim.data_points && dim.data_points.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {dim.data_points.map((dp: string, i: number) => (
                      <span key={i} className="text-[9px] bg-neutral-900 text-neutral-500 px-1.5 py-0.5 rounded">
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
        <div className="border border-neutral-800 rounded">
          <button onClick={() => toggle('catalysts')} className="flex w-full items-center justify-between px-4 py-2 hover:bg-neutral-900/50 transition-colors">
            <span className="text-xs font-medium text-neutral-300">Catalysts</span>
            <span className="text-neutral-600 text-xs">{expandedSection === 'catalysts' ? '−' : '+'}</span>
          </button>
          {expandedSection === 'catalysts' && (
            <div className="border-t border-neutral-800 px-4 py-3 space-y-1.5">
              {grade.catalystEvents.map((cat, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className={`text-[10px] px-1 py-0.5 rounded ${
                    cat.impact === 'positive' ? 'text-emerald-400' :
                    cat.impact === 'negative' ? 'text-red-400' :
                    'text-neutral-500'
                  }`}>
                    {cat.impact}
                  </span>
                  <div className="flex-1">
                    <span className="text-neutral-400">{cat.event}</span>
                    <span className="text-neutral-600 text-[10px] ml-1">
                      {cat.expected_date} · {(cat.probability * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Risks */}
      {grade.risks.length > 0 && (
        <div className="border border-neutral-800 rounded">
          <button onClick={() => toggle('risks')} className="flex w-full items-center justify-between px-4 py-2 hover:bg-neutral-900/50 transition-colors">
            <span className="text-xs font-medium text-neutral-300">Risks</span>
            <span className="text-neutral-600 text-xs">{expandedSection === 'risks' ? '−' : '+'}</span>
          </button>
          {expandedSection === 'risks' && (
            <div className="border-t border-neutral-800 px-4 py-3">
              <ul className="space-y-1">
                {grade.risks.map((risk, i) => (
                  <li key={i} className="flex gap-1.5 text-xs text-neutral-400">
                    <span className="text-red-400/60">•</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Contrarian */}
      {grade.contrarianSignal && (
        <div className="border border-yellow-900/30 rounded px-4 py-3">
          <span className="text-[10px] text-yellow-500/70 font-medium">CONTRARIAN</span>
          <p className="text-xs text-neutral-400 mt-0.5">{grade.contrarianSignal}</p>
        </div>
      )}

      {/* Data Gaps */}
      {grade.dataGaps && grade.dataGaps.length > 0 && (
        <div className="px-4 py-2">
          <p className="text-[10px] text-neutral-600">
            Data gaps: {grade.dataGaps.join(' · ')}
          </p>
        </div>
      )}
    </div>
  );
}
