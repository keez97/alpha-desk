import { LoadingState } from '../shared/LoadingState';
import { ErrorState } from '../shared/ErrorState';
import { useReportList, useDeleteReport } from '../../hooks/useWeeklyReport';
import { formatTimestamp } from '../../lib/utils';

interface ReportHistoryProps {
  selectedReportId?: string;
  onSelect: (id: string) => void;
}

export function ReportHistory({ selectedReportId, onSelect }: ReportHistoryProps) {
  const { data, isLoading, error, refetch } = useReportList();
  const { mutate: deleteReport } = useDeleteReport();

  if (isLoading) return <LoadingState message="Loading..." />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  return (
    <div className="h-full flex flex-col rounded-lg border border-gray-700 bg-gray-800/30">
      <div className="border-b border-gray-700 px-4 py-3">
        <h3 className="font-semibold text-white">Report History</h3>
        <p className="text-xs text-gray-500 mt-1">{data.length} reports</p>
      </div>

      <div className="flex-1 overflow-y-auto">
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-gray-500">
            <p className="text-sm">No reports generated yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {data.map((report: any) => (
              <button
                key={report.id}
                onClick={() => onSelect(report.id)}
                className={`w-full px-4 py-3 text-left hover:bg-gray-700/30 transition-colors border-l-2 ${
                  selectedReportId === report.id
                    ? 'border-blue-500 bg-gray-700/20'
                    : 'border-transparent'
                }`}
              >
                <p className="font-semibold text-white text-sm">{report.title}</p>
                <p className="text-xs text-gray-400 mt-1">{formatTimestamp(report.date)}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedReportId && (
        <div className="border-t border-gray-700 px-4 py-3">
          <button
            onClick={() => {
              deleteReport(selectedReportId);
            }}
            className="w-full rounded-lg bg-red-500/20 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Delete Report
          </button>
        </div>
      )}
    </div>
  );
}
