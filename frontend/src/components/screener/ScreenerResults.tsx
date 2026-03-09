import { useState } from 'react';
import { DataTable } from '../shared/DataTable';
import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { Timestamp } from '../shared/Timestamp';
import { useLatestScreener, useRunScreener } from '../../hooks/useScreener';

export function ScreenerResults() {
  const [activeTab, setActiveTab] = useState<'value' | 'momentum'>('value');
  const { data, isLoading, error, refetch } = useLatestScreener();
  const { mutate: runScreener, isPending } = useRunScreener();

  const columns = [
    { accessor: 'ticker' as const, header: 'Ticker', width: '80px' },
    { accessor: 'name' as const, header: 'Name', width: '150px' },
    { accessor: 'price' as const, header: 'Price', align: 'right' as const, format: 'currency' as const, width: '100px' },
    { accessor: 'changePercent' as const, header: 'Change', align: 'right' as const, format: 'delta' as const, width: '80px' },
    { accessor: 'pe' as const, header: 'P/E', align: 'right' as const, format: 'number' as const, width: '70px' },
    { accessor: 'pbv' as const, header: 'P/B', align: 'right' as const, format: 'number' as const, width: '70px' },
    { accessor: 'score' as const, header: 'Score', align: 'right' as const, format: 'number' as const, width: '70px' },
  ];

  if (isLoading) return <LoadingState message="Loading screener results..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  const hasResults = data && (data.valueOpportunities.length > 0 || data.momentumLeaders.length > 0);
  const activeData = activeTab === 'value'
    ? (data?.valueOpportunities || [])
    : (data?.momentumLeaders || []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-neutral-300">Screener</span>
          {data?.timestamp && <Timestamp date={data.timestamp} label="Generated" />}
        </div>
        <button
          onClick={() => runScreener()}
          disabled={isPending}
          className="px-3 py-1 rounded text-xs font-medium text-neutral-400 border border-neutral-800 hover:text-neutral-200 hover:border-neutral-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? 'Running...' : 'Run Screener'}
        </button>
      </div>

      {!hasResults ? (
        <div className="border border-neutral-800 rounded p-8 text-center">
          <p className="text-xs text-neutral-500 mb-3">No results. Run the screener to find opportunities.</p>
          <button
            onClick={() => runScreener()}
            disabled={isPending}
            className="px-4 py-1.5 rounded text-xs font-medium text-neutral-300 border border-neutral-700 hover:border-neutral-600 disabled:opacity-50 transition-colors"
          >
            {isPending ? 'Running...' : 'Run Screener'}
          </button>
        </div>
      ) : (
        <>
          <div className="flex gap-0.5 border-b border-neutral-800">
            {(['value', 'momentum'] as const).map((tab) => {
              const count = tab === 'value' ? data!.valueOpportunities.length : data!.momentumLeaders.length;
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors border-b-2 ${
                    activeTab === tab
                      ? 'text-neutral-200 border-neutral-400'
                      : 'text-neutral-500 border-transparent hover:text-neutral-300'
                  }`}
                >
                  {tab === 'value' ? 'Value' : 'Momentum'}
                  <span className="ml-1 text-neutral-600">({count})</span>
                </button>
              );
            })}
          </div>

          <div className="border border-neutral-800 rounded overflow-hidden">
            <DataTable columns={columns} data={activeData} sortable={true} />
          </div>
        </>
      )}
    </div>
  );
}
