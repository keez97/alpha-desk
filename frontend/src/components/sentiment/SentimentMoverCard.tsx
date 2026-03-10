import { SentimentMover } from '../../lib/api';
import { SentimentScore } from './SentimentScore';
import { classNames } from '../../lib/utils';

interface SentimentMoverCardProps {
  mover: SentimentMover;
  isSelected?: boolean;
  onClick: (ticker: string) => void;
}

export function SentimentMoverCard({
  mover,
  isSelected = false,
  onClick,
}: SentimentMoverCardProps) {
  const velocityArrow = mover.velocity > 0 ? '↑' : '↓';
  const velocityColor = mover.velocity > 0 ? 'text-emerald-400' : 'text-red-400';

  return (
    <div
      onClick={() => onClick(mover.ticker)}
      className={classNames(
        'p-3 rounded border transition-all cursor-pointer hover:bg-neutral-900',
        isSelected
          ? 'border-neutral-700 bg-neutral-900'
          : 'border-neutral-800 bg-[#0a0a0a] hover:border-neutral-700'
      )}
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-neutral-100 w-16">
            {mover.ticker}
          </span>
          <span className={classNames('text-xs font-semibold', velocityColor)}>
            {velocityArrow} {Math.abs(mover.velocity).toFixed(3)}
          </span>
        </div>
        <span className="text-[10px] text-neutral-500">
          {mover.article_count} articles
        </span>
      </div>

      {/* Score Bar */}
      <SentimentScore score={mover.sentiment_score} showLabel={false} size="sm" />

      {/* Sentiment Score Text */}
      <div className="text-xs text-neutral-400 mt-2">
        Score: {mover.sentiment_score.toFixed(2)}
      </div>
    </div>
  );
}
