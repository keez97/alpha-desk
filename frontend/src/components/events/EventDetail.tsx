import { LoadingState } from '../shared/LoadingState';
import { SeverityBadge } from './SeverityBadge';
import { AlphaDecayChart } from './AlphaDecayChart';
import type { EventDetail as EventDetailType } from '../../lib/api';

interface EventDetailProps {
  event: EventDetailType | null;
  isLoading?: boolean;
  alphaDecay?: any[];
  onDelete?: (id: number) => void;
  isDeleting?: boolean;
}

export function EventDetail({ event, isLoading = false, alphaDecay, onDelete, isDeleting = false }: EventDetailProps) {
  if (isLoading) {
    return <LoadingState message="Loading event details..." />;
  }

  if (!event) {
    return (
      <div className="border border-neutral-800 rounded p-4 text-center">
        <p className="text-xs text-neutral-500">Select an event to view details</p>
      </div>
    );
  }

  const eventDate = new Date(event.event_date);
  const detectedDate = new Date(event.detected_at);
  const dateStr = eventDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  const detectedStr = detectedDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="border border-neutral-800 rounded overflow-hidden flex flex-col h-full bg-black">
      {/* Header */}
      <div className="border-b border-neutral-800 p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg font-bold text-neutral-100">{event.ticker}</span>
              <SeverityBadge score={event.severity_score} showLabel />
            </div>
            <p className="text-xs text-neutral-400 line-clamp-2">{event.headline}</p>
          </div>
          {onDelete && (
            <button
              onClick={() => onDelete(event.id)}
              disabled={isDeleting}
              className="px-2 py-1 rounded text-[10px] font-medium text-neutral-500 border border-neutral-800 hover:text-neutral-300 hover:border-neutral-700 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </button>
          )}
        </div>
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto space-y-3 p-3">
        {/* Metadata */}
        <div className="space-y-1 border border-neutral-800 rounded p-2">
          <div className="grid grid-cols-2 gap-2 text-[10px]">
            <div>
              <p className="text-neutral-500 font-medium">Event Date</p>
              <p className="text-neutral-300">{dateStr}</p>
            </div>
            <div>
              <p className="text-neutral-500 font-medium">Detected</p>
              <p className="text-neutral-300">{detectedStr}</p>
            </div>
            <div>
              <p className="text-neutral-500 font-medium">Type</p>
              <p className="text-neutral-300">{event.event_type}</p>
            </div>
            <div>
              <p className="text-neutral-500 font-medium">Source</p>
              <p className="text-neutral-300 uppercase">{event.source}</p>
            </div>
          </div>
        </div>

        {/* Description */}
        {event.description && (
          <div className="space-y-1">
            <p className="text-[10px] font-medium text-neutral-400 uppercase">Description</p>
            <p className="text-xs text-neutral-400 leading-relaxed">{event.description}</p>
          </div>
        )}

        {/* Alpha Decay Chart */}
        {alphaDecay && alphaDecay.length > 0 && <AlphaDecayChart data={alphaDecay} />}

        {/* Additional Metadata */}
        {event.metadata && Object.keys(event.metadata).length > 0 && (
          <div className="space-y-1">
            <p className="text-[10px] font-medium text-neutral-400 uppercase">Additional Info</p>
            <div className="grid grid-cols-2 gap-1 text-[10px]">
              {Object.entries(event.metadata).map(([key, value]) => (
                <div key={key} className="border border-neutral-800 rounded p-1">
                  <p className="text-neutral-500 font-medium">{key}</p>
                  <p className="text-neutral-300 truncate">{String(value)}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
