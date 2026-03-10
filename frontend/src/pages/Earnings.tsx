import { useState, useMemo } from 'react';
import { EarningsCalendar } from '../components/earnings/EarningsCalendar';
import { EarningsDetail } from '../components/earnings/EarningsDetail';
import { useEarningsCalendar, useEarningsSignal, useEarningsHistory, useEarningsPEAD, useRefreshEarnings } from '../hooks/useEarnings';

export function Earnings() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  // Queries
  const { data: calendarData, isLoading: isCalendarLoading, error: calendarError } = useEarningsCalendar({
    page: 1,
    page_size: 100,
  });
  const { data: signalData, isLoading: isSignalLoading } = useEarningsSignal(selectedTicker);
  const { data: historyData, isLoading: isHistoryLoading } = useEarningsHistory(selectedTicker);
  const { data: peadData, isLoading: isPEADLoading } = useEarningsPEAD(selectedTicker);
  const { mutate: refreshEarnings, isPending: isRefreshing } = useRefreshEarnings();

  const calendarItems = useMemo(() => calendarData?.items || [], [calendarData]);

  const handleSelectTicker = (ticker: string) => {
    setSelectedTicker(ticker);
  };

  return (
    <div className="p-4 space-y-3 h-screen flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-neutral-100">Earnings Surprise Predictor</h1>
        <button
          onClick={() => refreshEarnings()}
          disabled={isRefreshing}
          className="px-3 py-1 rounded text-xs font-medium bg-neutral-800 hover:bg-neutral-700 disabled:opacity-50 transition-colors text-neutral-300"
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Left Panel: Calendar (60%) */}
        <div className="col-span-2 flex flex-col min-h-0 border border-neutral-800 rounded bg-[#0a0a0a]">
          <div className="p-3 border-b border-neutral-800">
            <h2 className="text-sm font-semibold text-neutral-100">Upcoming Earnings Calendar</h2>
          </div>
          <div className="flex-1 min-h-0 overflow-hidden">
            <EarningsCalendar
              items={calendarItems}
              selectedTicker={selectedTicker || undefined}
              onSelectTicker={handleSelectTicker}
              isLoading={isCalendarLoading}
              error={calendarError}
            />
          </div>
        </div>

        {/* Right Panel: Detail (40%) */}
        <div className="col-span-1 flex flex-col min-h-0 border border-neutral-800 rounded bg-[#0a0a0a]">
          <div className="p-3 border-b border-neutral-800">
            <h2 className="text-sm font-semibold text-neutral-100">Signal Details</h2>
          </div>
          <div className="flex-1 min-h-0 overflow-hidden p-3">
            <EarningsDetail
              signal={signalData || null}
              history={historyData?.quarters || null}
              pead={peadData?.quarters || null}
              isLoading={!selectedTicker}
              isHistoryLoading={isHistoryLoading}
              isPEADLoading={isPEADLoading}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
