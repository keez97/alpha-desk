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
    <div className="flex gap-px overflow-x-auto bg-neutral-900 border-b border-neutral-800">
      {data.indicators.map((indicator: any) => (
        <div key={indicator.name} className="flex-shrink-0 px-4 py-2 bg-black">
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider">{indicator.name}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="font-mono text-sm font-medium text-neutral-200">{indicator.value.toFixed(2)}</span>
            <DeltaBadge value={indicator.change} format="pct" />
          </div>
        </div>
      ))}
    </div>
  );
}
