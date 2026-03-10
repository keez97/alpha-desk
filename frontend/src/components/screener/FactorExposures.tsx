import type { StockFactorData } from '../../lib/api';
import { useStockFactors } from '../../hooks/useStockFactors';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { classNames } from '../../lib/utils';

function getBarColor(percentile: number): string {
  if (percentile >= 67) return 'bg-green-600';
  if (percentile >= 33) return 'bg-amber-600';
  return 'bg-red-600';
}

function getSignalText(signal: string): string {
  const signalMap: Record<string, string> = {
    strong: 'Strong',
    neutral: 'Neutral',
    weak: 'Weak',
  };
  return signalMap[signal] || signal;
}

function getSignalColor(signal: string): string {
  const colorMap: Record<string, string> = {
    strong: 'text-green-400',
    neutral: 'text-neutral-400',
    weak: 'text-red-400',
  };
  return colorMap[signal] || 'text-neutral-400';
}

interface FactorExposuresProps {
  ticker: string | null;
}

export function FactorExposures({ ticker }: FactorExposuresProps) {
  const { data, isLoading, error, refetch } = useStockFactors(ticker);

  if (!ticker) return null;
  if (isLoading) return <LoadingState message="Loading factor exposures..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data || data.length === 0) return null;

  return (
    <div className="space-y-3">
      <div className="text-xs font-medium text-neutral-300">Factor Exposures</div>

      <div className="space-y-2">
        {data.map((factor: StockFactorData) => (
          <div key={factor.name} className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-neutral-400 flex-1">{factor.name}</span>
              <span className={classNames('text-[10px] font-mono font-medium', getSignalColor(factor.signal))}>
                {getSignalText(factor.signal)}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex-1 bg-neutral-800 rounded h-1.5 overflow-hidden">
                <div
                  className={classNames('h-full transition-all', getBarColor(factor.percentile))}
                  style={{ width: `${factor.percentile}%` }}
                />
              </div>
              <span className="text-[10px] font-mono text-neutral-500 w-12 text-right">
                {factor.value.toFixed(2)}
              </span>
            </div>

            <div className="text-[9px] text-neutral-600">
              Percentile: {factor.percentile}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
