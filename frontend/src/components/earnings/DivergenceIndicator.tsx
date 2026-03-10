import { classNames } from '../../lib/utils';

interface DivergenceIndicatorProps {
  divergence: number;
  signal: 'buy' | 'sell' | 'hold';
}

export function DivergenceIndicator({ divergence, signal }: DivergenceIndicatorProps) {
  const absDivergence = Math.abs(divergence);
  const isHighConviction = absDivergence >= 2;

  const getColor = () => {
    if (signal === 'buy') return 'bg-emerald-400';
    if (signal === 'sell') return 'bg-red-400';
    return 'bg-neutral-600';
  };

  const getBackgroundColor = () => {
    if (signal === 'buy') return 'bg-emerald-950';
    if (signal === 'sell') return 'bg-red-950';
    return 'bg-neutral-900';
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] text-neutral-500 font-medium">Divergence</span>
        <span
          className={classNames(
            'text-xs font-semibold',
            isHighConviction ? 'text-emerald-400' : 'text-neutral-400'
          )}
        >
          {divergence > 0 ? '+' : ''}{divergence.toFixed(2)}%
        </span>
      </div>

      {/* Bar visual */}
      <div className={classNames('h-1.5 rounded-full overflow-hidden', getBackgroundColor())}>
        <div
          className={classNames('h-full rounded-full transition-all', getColor())}
          style={{
            width: `${Math.min(100, Math.abs(divergence) * 20)}%`,
          }}
        />
      </div>

      {isHighConviction && (
        <div className="text-[10px] text-emerald-400 font-medium">HIGH CONVICTION</div>
      )}
    </div>
  );
}
