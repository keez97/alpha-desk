import { DeltaBadge } from '../shared/DeltaBadge';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useMacro } from '../../hooks/useMacro';

export function MacroBar() {
  const { data, isLoading, error, refetch } = useMacro();

  if (isLoading) return <LoadingState message="Loading macro data..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div className="flex space-x-1 overflow-x-auto bg-gray-800/30 px-4 py-3 border-b border-gray-700">
      {data.indicators.map((indicator: any) => (
        <div key={indicator.name} className="flex-shrink-0 px-4 py-2 bg-gray-800/50 rounded-lg border border-gray-700">
          <div className="text-xs text-gray-400">{indicator.name}</div>
          <div className="flex items-center space-x-2 mt-1">
            <span className="font-mono font-semibold text-white">{indicator.value.toFixed(2)}</span>
            <DeltaBadge value={indicator.change} format="pct" />
          </div>
        </div>
      ))}
    </div>
  );
}
