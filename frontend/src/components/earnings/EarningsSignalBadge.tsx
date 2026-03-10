import { classNames } from '../../lib/utils';

interface EarningsSignalBadgeProps {
  signal: 'buy' | 'sell' | 'hold';
  confidence: number;
  showConfidence?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function EarningsSignalBadge({
  signal,
  confidence,
  showConfidence = true,
  size = 'md',
}: EarningsSignalBadgeProps) {
  const getSignalStyles = (sig: string, sz: string) => {
    const baseClasses = 'font-semibold flex items-center gap-1';

    if (sig === 'buy') {
      return classNames(
        baseClasses,
        sz === 'sm' ? 'text-[10px]' : sz === 'lg' ? 'text-sm' : 'text-xs',
        'text-emerald-400'
      );
    } else if (sig === 'sell') {
      return classNames(
        baseClasses,
        sz === 'sm' ? 'text-[10px]' : sz === 'lg' ? 'text-sm' : 'text-xs',
        'text-red-400'
      );
    } else {
      return classNames(
        baseClasses,
        sz === 'sm' ? 'text-[10px]' : sz === 'lg' ? 'text-sm' : 'text-xs',
        'text-neutral-500'
      );
    }
  };

  const getArrow = (sig: string) => {
    if (sig === 'buy') return '↑';
    if (sig === 'sell') return '↓';
    return '→';
  };

  return (
    <div className="flex flex-col gap-1">
      <div className={getSignalStyles(signal, size)}>
        <span>{getArrow(signal)}</span>
        <span>{signal.toUpperCase()}</span>
      </div>
      {showConfidence && (
        <div className={classNames('text-[10px] text-neutral-500 font-medium')}>
          {(confidence * 100).toFixed(0)}% confidence
        </div>
      )}
    </div>
  );
}
