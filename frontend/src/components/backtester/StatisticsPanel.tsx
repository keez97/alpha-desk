import type { BacktestResult } from '../../lib/api';

interface StatisticsPanelProps {
  results: BacktestResult;
}

const stats = [
  { key: 'sharpe_ratio', label: 'Sharpe Ratio', format: (v: number) => v.toFixed(2) },
  { key: 'sortino_ratio', label: 'Sortino Ratio', format: (v: number) => v.toFixed(2) },
  { key: 'calmar_ratio', label: 'Calmar Ratio', format: (v: number) => v.toFixed(2) },
  { key: 'max_drawdown', label: 'Max Drawdown', format: (v: number) => (v * 100).toFixed(2) + '%' },
  { key: 'information_ratio', label: 'Information Ratio', format: (v: number) => v.toFixed(2) },
  { key: 'hit_rate', label: 'Hit Rate', format: (v: number) => (v * 100).toFixed(1) + '%' },
  { key: 'annualized_return', label: 'Annualized Return', format: (v: number) => (v * 100).toFixed(2) + '%' },
  { key: 'annualized_volatility', label: 'Annualized Volatility', format: (v: number) => (v * 100).toFixed(2) + '%' },
  { key: 'total_return', label: 'Total Return', format: (v: number) => (v * 100).toFixed(2) + '%' },
  { key: 'best_day', label: 'Best Day', format: (v: number) => (v * 100).toFixed(2) + '%' },
  { key: 'worst_day', label: 'Worst Day', format: (v: number) => (v * 100).toFixed(2) + '%' },
  { key: 'avg_turnover', label: 'Avg Turnover', format: (v: number) => (v * 100).toFixed(2) + '%' },
];

export function StatisticsPanel({ results }: StatisticsPanelProps) {
  const getValue = (key: string) => {
    const parts = key.split('_');
    let current: any = results.statistics;
    for (const part of parts) {
      current = current?.[part];
    }
    return current;
  };

  const isPositive = (key: string, value: number): boolean => {
    // For drawdown, positive means lower (better)
    if (key === 'max_drawdown' || key === 'worst_day') return value < 0;
    // For most metrics, positive is better
    return value >= 0;
  };

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-4 bg-black">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">Statistics</span>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {stats.map((stat) => {
          const value = getValue(stat.key);
          const positive = isPositive(stat.key, value);
          const textColor = positive ? 'text-green-400/70' : 'text-red-400/70';

          return (
            <div key={stat.key} className="border border-neutral-800 rounded p-3 bg-neutral-900/20">
              <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-500">{stat.label}</p>
              <p className={`text-sm font-mono mt-1 ${textColor}`}>{stat.format(value)}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
