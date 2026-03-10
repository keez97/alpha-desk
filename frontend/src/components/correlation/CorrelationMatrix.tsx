import { useState, useMemo } from 'react';
import type { CorrelationData } from '../../hooks/useCorrelation';

interface CorrelationMatrixProps {
  data: CorrelationData;
  onPairSelect?: (ticker1: string, ticker2: string) => void;
}

/**
 * Get color for correlation value
 * Green (positive): deep > 0.8, light 0.5-0.8
 * Neutral: 0-0.5
 * Red (negative): light -0.5-0, deep < -0.5
 */
function getCorrelationColor(value: number): {
  bg: string;
  text: string;
  border?: string;
} {
  if (value > 0.8) {
    return { bg: 'bg-green-950', text: 'text-green-300' };
  } else if (value > 0.5) {
    return { bg: 'bg-green-900', text: 'text-green-200' };
  } else if (value > 0) {
    return { bg: 'bg-neutral-700', text: 'text-green-100' };
  } else if (value > -0.3) {
    return { bg: 'bg-neutral-700', text: 'text-neutral-300' };
  } else if (value > -0.5) {
    return { bg: 'bg-red-900', text: 'text-red-200' };
  } else {
    return { bg: 'bg-red-950', text: 'text-red-300' };
  }
}

export function CorrelationMatrix({
  data,
  onPairSelect,
}: CorrelationMatrixProps) {
  const [hoveredCell, setHoveredCell] = useState<{
    i: number;
    j: number;
  } | null>(null);

  if (
    !data.matrix ||
    data.matrix.length === 0 ||
    !data.tickers ||
    data.tickers.length === 0
  ) {
    return (
      <div className="p-6 bg-neutral-800 rounded border border-neutral-700 text-center">
        <p className="text-neutral-400">No correlation data available</p>
      </div>
    );
  }

  const n = data.tickers.length;

  // For display, show max 11 tickers (most common case)
  const displayTickers = data.tickers.slice(0, 11);
  const displayMatrix = data.matrix.slice(0, 11).map((row) => row.slice(0, 11));

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-sm font-semibold text-neutral-100 mb-2">
          Correlation Matrix
        </h3>
        <p className="text-xs text-neutral-400">
          {data.lookback_days}-day rolling correlation between sector ETFs
        </p>
      </div>

      {/* Matrix Table */}
      <div className="overflow-x-auto bg-neutral-900 rounded border border-neutral-800">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr>
              <th className="w-16 h-16 bg-neutral-800 border border-neutral-700 p-0"></th>
              {displayTickers.map((ticker, j) => (
                <th
                  key={j}
                  className="w-12 h-16 bg-neutral-800 border border-neutral-700 p-1 align-bottom"
                >
                  <div className="text-center transform -rotate-45 origin-center whitespace-nowrap text-neutral-300 font-medium">
                    {ticker}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayMatrix.map((row, i) => (
              <tr key={i}>
                {/* Row header */}
                <td className="bg-neutral-800 border border-neutral-700 p-1 font-medium text-neutral-300 text-center">
                  {displayTickers[i]}
                </td>

                {/* Cells */}
                {row.map((corr, j) => {
                  const isDiagonal = i === j;
                  const isHovered =
                    hoveredCell &&
                    ((hoveredCell.i === i && hoveredCell.j === j) ||
                      (hoveredCell.i === j && hoveredCell.j === i));

                  const colors = getCorrelationColor(corr);

                  return (
                    <td
                      key={j}
                      className={`border border-neutral-700 p-1 text-center cursor-pointer transition-all ${
                        isDiagonal
                          ? 'bg-neutral-900 border-neutral-600'
                          : colors.bg
                      } ${isHovered ? 'ring-2 ring-offset-1 ring-blue-500' : ''}`}
                      onMouseEnter={() => setHoveredCell({ i, j })}
                      onMouseLeave={() => setHoveredCell(null)}
                      onClick={() => {
                        if (!isDiagonal && onPairSelect) {
                          onPairSelect(displayTickers[i], displayTickers[j]);
                        }
                      }}
                      title={`${displayTickers[i]} vs ${displayTickers[j]}: ${corr.toFixed(2)}`}
                    >
                      <span
                        className={`font-semibold ${
                          isDiagonal
                            ? 'text-neutral-500'
                            : colors.text
                        }`}
                      >
                        {isDiagonal ? '1.00' : corr.toFixed(2)}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="bg-neutral-800 rounded border border-neutral-700 p-3">
        <p className="text-xs font-medium text-neutral-400 mb-2">Legend</p>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-green-950 rounded border border-neutral-700"></div>
            <span className="text-neutral-300">Very High (&gt;0.8)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-green-900 rounded border border-neutral-700"></div>
            <span className="text-neutral-300">High (0.5-0.8)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-neutral-700 rounded border border-neutral-700"></div>
            <span className="text-neutral-300">Low (-0.3 to 0.5)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-red-900 rounded border border-neutral-700"></div>
            <span className="text-neutral-300">Negative (-0.5 to -0.3)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-red-950 rounded border border-neutral-700"></div>
            <span className="text-neutral-300">Very Negative (&lt;-0.5)</span>
          </div>
        </div>
      </div>

      {/* Hover Tooltip */}
      {hoveredCell && hoveredCell.i !== hoveredCell.j && (
        <div className="text-xs text-neutral-400 p-2 bg-neutral-800 rounded border border-neutral-700">
          <p className="font-medium text-neutral-200">
            {displayTickers[hoveredCell.i]} ↔ {displayTickers[hoveredCell.j]}
          </p>
          <p>
            Correlation:{' '}
            <span className="font-semibold text-neutral-100">
              {displayMatrix[hoveredCell.i][hoveredCell.j].toFixed(2)}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
