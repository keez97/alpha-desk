import { classNames } from '../../lib/utils';

interface SentimentScoreProps {
  score: number;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function SentimentScore({ score, showLabel = true, size = 'md' }: SentimentScoreProps) {
  const clampedScore = Math.min(Math.max(score, -1), 1);
  const percentage = (clampedScore + 1) / 2 * 100;

  const getLabel = (s: number) => {
    if (s > 0.3) return 'Bullish';
    if (s < -0.3) return 'Bearish';
    return 'Neutral';
  };

  const getColor = (s: number) => {
    if (s > 0) return 'bg-emerald-500';
    if (s < 0) return 'bg-red-500';
    return 'bg-neutral-600';
  };

  const getTextColor = (s: number) => {
    if (s > 0) return 'text-emerald-400';
    if (s < 0) return 'text-red-400';
    return 'text-neutral-400';
  };

  const barHeight =
    size === 'sm' ? 'h-1' : size === 'lg' ? 'h-4' : 'h-2';

  const textSize =
    size === 'sm' ? 'text-[10px]' : size === 'lg' ? 'text-sm' : 'text-xs';

  return (
    <div className="flex flex-col gap-1">
      {/* Bar */}
      <div className={classNames('w-full bg-neutral-800 rounded overflow-hidden', barHeight)}>
        <div
          className={classNames(
            getColor(clampedScore),
            'h-full transition-all duration-300'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Label and Score */}
      {showLabel && (
        <div className="flex items-center justify-between">
          <span className={classNames('font-semibold', textSize, getTextColor(clampedScore))}>
            {getLabel(clampedScore)}
          </span>
          <span className={classNames('font-semibold', textSize, getTextColor(clampedScore))}>
            {clampedScore.toFixed(2)}
          </span>
        </div>
      )}
    </div>
  );
}
