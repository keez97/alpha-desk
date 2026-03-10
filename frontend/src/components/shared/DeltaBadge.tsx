import { classNames, formatPercent } from '../../lib/utils';

interface DeltaBadgeProps {
  value: number | undefined | null;
  format?: 'pct' | 'abs';
}

export function DeltaBadge({ value, format = 'pct' }: DeltaBadgeProps) {
  if (value == null || isNaN(value)) {
    return <span className="inline-block text-[11px] font-mono text-neutral-500">—</span>;
  }
  const isPositive = value > 0;
  const isNegative = value < 0;

  const displayValue = format === 'pct' ? formatPercent(value) : `${value.toFixed(2)}`;

  return (
    <span
      className={classNames(
        'inline-block text-[11px] font-mono font-medium',
        isPositive && 'text-emerald-400',
        isNegative && 'text-red-400',
        !isPositive && !isNegative && 'text-neutral-500'
      )}
    >
      {displayValue}
    </span>
  );
}
