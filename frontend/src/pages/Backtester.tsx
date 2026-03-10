import { useState, useEffect } from 'react';
import { BacktestConfig } from '../components/backtester/BacktestConfig';
import { BacktestProgress } from '../components/backtester/BacktestProgress';
import { BacktestResults } from '../components/backtester/BacktestResults';
import { BacktestHistory } from '../components/backtester/BacktestHistory';
import { useBacktestStatus, useBacktestResults } from '../hooks/useBacktester';
import type { Backtest } from '../lib/api';

export function Backtester() {
  const [selectedBacktest, setSelectedBacktest] = useState<Backtest | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // Poll status while running
  const { data: statusData } = useBacktestStatus(selectedBacktest?.id, isRunning);
  const { data: resultsData, isLoading: resultsLoading } = useBacktestResults(selectedBacktest?.id);

  // Update running state based on status
  useEffect(() => {
    if (statusData?.status === 'completed' || statusData?.status === 'failed') {
      setIsRunning(false);
    }
  }, [statusData?.status]);

  const handleBacktestSubmit = (backtest: Backtest) => {
    setSelectedBacktest(backtest);
    setIsRunning(true);
  };

  const handleSelectBacktest = (backtest: Backtest) => {
    setSelectedBacktest(backtest);
    setIsRunning(false);
  };

  const handleDeleteBacktest = () => {
    setSelectedBacktest(null);
  };

  return (
    <div className="p-4 flex gap-4 h-[calc(100vh-3rem)]">
      {/* Sidebar */}
      <div className="w-80 shrink-0 overflow-y-auto space-y-3">
        <BacktestConfig onSubmit={handleBacktestSubmit} isRunning={isRunning} />
        <BacktestHistory
          selectedId={selectedBacktest?.id}
          onSelect={handleSelectBacktest}
          onDelete={handleDeleteBacktest}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto">
        {isRunning && statusData ? (
          <BacktestProgress status={statusData} />
        ) : selectedBacktest ? (
          <BacktestResults
            backtest={selectedBacktest}
            results={resultsData}
            isLoading={resultsLoading}
          />
        ) : (
          <div className="border border-neutral-800 rounded p-4 bg-black h-full flex items-center justify-center">
            <div className="text-center">
              <p className="text-sm text-neutral-400">No backtest selected</p>
              <p className="text-xs text-neutral-600 mt-1">Create a new backtest or select one from history</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
