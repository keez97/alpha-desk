import { classNames } from '../../lib/utils';
import { SeverityBadge } from './SeverityBadge';
import type { EventItem } from '../../lib/api';

interface EventCardProps {
  event: EventItem;
  isActive?: boolean;
  onClick?: (event: EventItem) => void;
}

export function EventCard({ event, isActive = false, onClick }: EventCardProps) {
  const eventDate = new Date(event.event_date);
  const detectedDate = new Date(event.detected_at);
  const dateStr = eventDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const sourceLabel = event.source?.toUpperCase() || 'UNKNOWN';

  return (
    <div
      onClick={() => onClick?.(event)}
      className={classNames(
        'border border-neutral-800 rounded p-3 cursor-pointer transition-colors hover:border-neutral-700',
        isActive ? 'border-neutral-400 bg-neutral-900' : 'hover:bg-neutral-950'
      )}
    >
      <div className="flex items-center gap-3">
        {/* Left: Severity Badge, Type, Ticker */}
        <div className="flex items-center gap-2 min-w-0 flex-shrink-0">
          <SeverityBadge score={event.severity_score} />
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wide">{event.ticker}</span>
            <span className="text-[10px] text-neutral-500">{event.event_type}</span>
          </div>
        </div>

        {/* Center: Headline and Date */}
        <div className="flex-1 min-w-0">
          <p className="text-xs text-neutral-300 truncate">{event.headline}</p>
          <p className="text-[10px] text-neutral-500 mt-0.5">{dateStr}</p>
        </div>

        {/* Right: Source Badge */}
        <div className="flex-shrink-0">
          <span className="inline-block px-2 py-0.5 rounded text-[9px] font-medium text-neutral-400 border border-neutral-700 bg-neutral-900">
            {sourceLabel}
          </span>
        </div>
      </div>
    </div>
  );
}
