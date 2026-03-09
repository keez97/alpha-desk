import { Backtest } from '../../lib/api';
import { useBacktestList, useDeleteBacktest } from '../../hooks/useBacktester';
import { LoadingState } from '../shared/LoadingState';

interface BacktestHistoryProps {
  selectedId?: number | null;
  onSelect: (backtest: Backtest) => void;
  onDelete?: () => void;
}

function getStatusBadgeColor(status: string): string {
  switch (status) {
    case 'completed':
      return 'bg-green-900/30 text-green-400';
    case 'running':
      return 'bg-yellow-900/30 text-yellow-400';
    case 'failed':
      return 'bg-red-900/30 text-red-400';
    default:
      return 'bg-neutral-900/30 text-neutral-400';
  }
}

export function BacktestHistory({ selectedId, onSelect, onDelete }: BacktestHistoryProps) {
  const { data: backtests, isLoading } = useBacktestList();
  const { mutate: deleteBacktest } = useDeleteBacktest();

  if (isLoading) {
    return <LoadingState message="Loading history..." />;
  }

  const handleDelete = (id: number) => {
    if (confirm('Delete this backtest?')) {
      deleteBacktest(id, {
        onSuccess: () => {
          if (onDelete) {
            onDelete();
          }
        },
      });
    }
  };

  return (
    <div className="border border-neutral-800 rounded p-4 space-y-3 bg-black">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-500">History</span>
        <span className="text-[10px] text-neutral-600">{backtests?.length || 0}</span>
      </div>

      {!backtests || backtests.length === 0 ? (
        <p className="text-[10px] text-neutral-600">No backtests yet</p>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {backtests.map((backtest: Backtest) => (
            <div
              key={backtest.id}
              className={`border rounded p-2 transition-colors cursor-pointer ${
                selectedId === backtest.id ? 'border-neutral-600 bg-neutral-900/50' : 'border-neutral-800 hover:border-neutral-700 hover:bg-neutral-900/30'
              }`}
              onClick={() => onSelect(backtest)}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-neutral-200 truncate">{backtest.name}</p>
                  <p className="text-[10px] text-neutral-600 mt-0.5">
                    {new Date(backtest.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium uppercase tracking-wider flex-shrink-0 ${getStatusBadgeColor(backtest.status)}`}>
                  {backtest.status}
                </span>
              </div>
              {backtest.results?.statistics && (
                <div className="mt-1.5 text-[10px] text-neutral-500">
                  <p>Sharpe: <span className="text-neutral-400 font-mono">{backtest.results.statistics.sharpe_ratio.toFixed(2)}</span></p>
                </div>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(backtest.id);
                }}
                className="mt-1.5 w-full py-1 rounded text-[10px] text-red-400/70 hover:text-red-400 hover:bg-red-900/20 transition-colors"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
