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
    <div className="h-full flex flex-col border border-neutral-800 rounded">
      <div className="border-b border-neutral-800 px-3 py-2">
        <span className="text-xs font-medium text-neutral-300">History</span>
        <span className="text-[10px] text-neutral-600 ml-2">{data.length}</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {data.length === 0 ? (
          <div className="flex items-center justify-center h-24 text-neutral-600">
            <p className="text-xs">No reports yet</p>
          </div>
        ) : (
          <div className="divide-y divide-neutral-900">
            {data.map((report: any) => (
              <button
                key={report.id}
                onClick={() => onSelect(report.id)}
                className={`w-full px-3 py-2 text-left hover:bg-neutral-900/50 transition-colors border-l-2 ${
                  selectedReportId === report.id
                    ? 'border-neutral-400 bg-neutral-900/30'
                    : 'border-transparent'
                }`}
              >
                <p className="text-xs text-neutral-200 font-medium">{report.title}</p>
                <p className="text-[10px] text-neutral-600 mt-0.5">{formatTimestamp(report.date)}</p>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedReportId && (
        <div className="border-t border-neutral-800 px-3 py-2">
          <button
            onClick={() => {
              deleteReport(selectedReportId);
            }}
            className="text-[10px] text-red-400/60 hover:text-red-400 transition-colors"
          >
            Delete Report
          </button>
        </div>
      )}
    </div>
  );
}
