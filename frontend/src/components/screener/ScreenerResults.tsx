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
  if (!data) return null;

  const activeData = activeTab === 'value' ? data.valueOpportunities : data.momentumLeaders;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Screener Results</h2>
          <Timestamp date={data.timestamp} label="Generated" />
        </div>
        <button
          onClick={() => runScreener()}
          disabled={isPending}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {isPending ? 'Running...' : 'Run Screener'}
        </button>
      </div>

      <div className="flex space-x-2 border-b border-gray-700">
        {(['value', 'momentum'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium transition-colors border-b-2 ${
              activeTab === tab
                ? 'text-blue-400 border-blue-500'
                : 'text-gray-400 border-transparent hover:text-gray-300'
            }`}
          >
            {tab === 'value' ? 'Value Opportunities' : 'Momentum Leaders'}
            <span className="ml-2 text-xs">({activeData.length})</span>
          </button>
        ))}
      </div>

      <div className="bg-gray-800/30 rounded-lg border border-gray-700 overflow-hidden">
        <DataTable columns={columns} data={activeData} sortable={true} />
      </div>
    </div>
  );
}
