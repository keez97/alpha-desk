import { useState } from 'react';
import { EventCard } from './EventCard';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import type { EventItem } from '../../lib/api';

interface EventTimelineProps {
  events: EventItem[];
  isLoading?: boolean;
  error?: Error | null;
  selectedEventId?: number;
  onSelectEvent?: (event: EventItem) => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  onRetry?: () => void;
}

export function EventTimeline({
  events,
  isLoading = false,
  error = null,
  selectedEventId,
  onSelectEvent,
  onLoadMore,
  hasMore = false,
  isLoadingMore = false,
  onRetry,
}: EventTimelineProps) {
  const [scrolled, setScrolled] = useState(false);

  if (isLoading && !scrolled) {
    return <LoadingState message="Loading events..." />;
  }

  if (error && !events.length) {
    return <ErrorState error={error} onRetry={onRetry} />;
  }

  if (!events.length && !isLoading) {
    return (
      <div className="border border-neutral-800 rounded p-8 text-center">
        <p className="text-sm text-neutral-300 font-medium mb-2">No events found</p>
        <p className="text-xs text-neutral-500">Use the scan button to detect upcoming events, or events will populate automatically as market data is collected.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 max-h-[calc(100vh-200px)] overflow-y-auto">
      {events.map((event) => (
        <EventCard
          key={event.id}
          event={event}
          isActive={selectedEventId === event.id}
          onClick={onSelectEvent}
        />
      ))}

      {isLoadingMore && (
        <div className="p-3 text-center">
          <p className="text-[10px] text-neutral-500">Loading more events...</p>
        </div>
      )}

      {hasMore && !isLoadingMore && (
        <button
          onClick={() => {
            setScrolled(true);
            onLoadMore?.();
          }}
          className="w-full px-3 py-2 rounded text-xs font-medium text-neutral-400 border border-neutral-800 hover:text-neutral-200 hover:border-neutral-700 transition-colors"
        >
          Load More
        </button>
      )}
    </div>
  );
}
