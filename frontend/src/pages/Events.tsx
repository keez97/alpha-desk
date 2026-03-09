import { useState, useMemo } from 'react';
import { EventFilters } from '../components/events/EventFilters';
import { EventTimeline } from '../components/events/EventTimeline';
import { EventDetail } from '../components/events/EventDetail';
import { ScanButton } from '../components/events/ScanButton';
import { useEvents, useEventDetail, useAlphaDecay, usePollingStatus, useTriggerScan, useDeleteEvent, type EventFilters as EventFiltersType } from '../hooks/useEvents';

export function Events() {
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [filters, setFilters] = useState<EventFiltersType>({});
  const [currentPage, setCurrentPage] = useState(1);

  // Queries
  const { data: eventsData, isLoading, error, refetch } = useEvents({ ...filters, page: currentPage, page_size: 20 });
  const { data: eventDetail, isLoading: detailLoading } = useEventDetail(selectedEventId);
  const { data: alphaDecay } = useAlphaDecay(selectedEventId);
  const { data: pollingStatus } = usePollingStatus();
  const { mutate: triggerScan, isPending: isScanning } = useTriggerScan();
  const { mutate: deleteEvent, isPending: isDeleting } = useDeleteEvent();

  const events = useMemo(() => eventsData?.items || [], [eventsData]);
  const totalPages = useMemo(() => (eventsData ? Math.ceil(eventsData.total / (eventsData.page_size || 20)) : 0), [eventsData]);

  const handleSelectEvent = (eventId: number) => {
    setSelectedEventId(eventId);
  };

  const handleFiltersChange = (newFilters: EventFiltersType) => {
    setFilters(newFilters);
    setCurrentPage(1);
    setSelectedEventId(null);
  };

  const handleLoadMore = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handleDelete = (id: number) => {
    if (confirm('Are you sure you want to delete this event?')) {
      deleteEvent(id, {
        onSuccess: () => {
          setSelectedEventId(null);
        },
      });
    }
  };

  return (
    <div className="p-4 space-y-3 h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-neutral-100">Event Scanner</h1>
        <div className="text-xs text-neutral-500">
          {eventsData && `${events.length} of ${eventsData.total} events`}
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Left Panel: Timeline Feed (60%) */}
        <div className="col-span-2 space-y-3 flex flex-col min-h-0">
          {/* Filters */}
          <EventFilters onFiltersChange={handleFiltersChange} />

          {/* Event Timeline */}
          <div className="flex-1 min-h-0 overflow-y-auto">
            <EventTimeline
              events={events}
              isLoading={isLoading}
              error={error}
              selectedEventId={selectedEventId || undefined}
              onSelectEvent={(event) => handleSelectEvent(event.id)}
              onLoadMore={handleLoadMore}
              hasMore={currentPage < totalPages}
              onRetry={() => refetch()}
            />
          </div>

          {/* Scan Controls */}
          <ScanButton onScan={() => triggerScan()} isScanning={isScanning} pollingStatus={pollingStatus || undefined} />
        </div>

        {/* Right Panel: Detail (40%) */}
        <div className="col-span-1 flex flex-col min-h-0">
          <EventDetail
            event={eventDetail || null}
            isLoading={detailLoading}
            alphaDecay={alphaDecay}
            onDelete={handleDelete}
            isDeleting={isDeleting}
          />
        </div>
      </div>
    </div>
  );
}
