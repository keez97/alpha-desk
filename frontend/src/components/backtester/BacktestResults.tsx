import { Backtest, BacktestResult } from '../../lib/api';
import { StatisticsPanel } from './StatisticsPanel';
import { EquityCurveChart } from './EquityCurveChart';
import { FactorExposureChart } from './FactorExposureChart';
import { CorrelationMatrix } from './CorrelationMatrix';
import { AlphaDecayPanel } from './AlphaDecayPanel';
import { ExportButton } from './ExportButton';

interface BacktestResultsProps {
  backtest: Backtest;
  results: BacktestResult | undefined;
  isLoading: boolean;
  onExport?: () => void;
}

export function BacktestResults({ backtest, results, isLoading, onExport }: BacktestResultsProps) {
  if (isLoading) {
    return (
      <div className="border border-neutral-800 rounded p-4 bg-black">
        <p className="text-xs text-neutral-500">Loading results...</p>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="border border-neutral-800 rounded p-4 bg-black">
        <p className="text-xs text-neutral-500">No results available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
        <div>
          <h2 className="text-sm font-medium text-neutral-200">{backtest.name}</h2>
          <p className="text-[10px] text-neutral-600 mt-1">
            Created {new Date(backtest.created_at).toLocaleDateString()}
          </p>
        </div>
        <ExportButton backtestId={backtest.id} onExport={onExport} />
      </div>

      <StatisticsPanel results={results} />
      <EquityCurveChart results={results} />
      <FactorExposureChart results={results} />
      <CorrelationMatrix results={results} />
      <AlphaDecayPanel results={results} />
    </div>
  );
}
