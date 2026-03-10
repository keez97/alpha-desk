import type { BacktestStatus } from '../../lib/api';

interface BacktestProgressProps {
  status: BacktestStatus | undefined;
}

export function BacktestProgress({ status }: BacktestProgressProps) {
  const progress = status?.progress_percent || 0;

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-4 bg-black">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">Backtest Running</span>
        <span className="text-sm font-mono text-neutral-400">{Math.round(progress)}%</span>
      </div>

      <div className="relative h-2 bg-neutral-900 rounded overflow-hidden border border-neutral-800">
        <div
          className="absolute top-0 left-0 h-full bg-neutral-400 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {status?.current_rebalance_date && (
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">Current Rebalance</p>
          <p className="text-xs text-neutral-300 mt-1">{status.current_rebalance_date}</p>
        </div>
      )}

      <div className="text-[10px] text-neutral-500">
        <p>Status: <span className="text-neutral-400">{status?.status || 'running'}</span></p>
      </div>
    </div>
  );
}
