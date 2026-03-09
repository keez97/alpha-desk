import { classNames, formatPercent } from '../../lib/utils';

interface DeltaBadgeProps {
  value: number;
  format?: 'pct' | 'abs';
}

export function DeltaBadge({ value, format = 'pct' }: DeltaBadgeProps) {
  const isPositive = value > 0;
  const isNegative = value < 0;

  const displayValue = format === 'pct' ? formatPercent(value) : `${value.toFixed(2)}`;

  return (
    <span
      className={classNames(
        'inline-block rounded px-2 py-1 text-xs font-mono font-medium',
        isPositive && 'bg-green-500/20 text-green-400',
        isNegative && 'bg-red-500/20 text-red-400',
        !isPositive && !isNegative && 'bg-gray-500/20 text-gray-400'
      )}
    >
      {displayValue}
    </span>
  );
}
