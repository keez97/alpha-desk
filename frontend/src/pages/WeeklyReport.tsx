import { useState } from 'react';
import { ReportGenerator } from '../components/weekly-report/ReportGenerator';
import { ReportViewer } from '../components/weekly-report/ReportViewer';
import { ReportHistory } from '../components/weekly-report/ReportHistory';
import { useReport } from '../hooks/useWeeklyReport';
import { LoadingState } from '../components/shared/LoadingState';
import { ErrorState } from '../components/shared/ErrorState';

export function WeeklyReport() {
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const { data: report, isLoading, error, refetch } = useReport(selectedReportId);

  return (
    <div className="p-4 space-y-3">
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-4">
          {!selectedReportId ? (
            <ReportGenerator />
          ) : isLoading ? (
            <LoadingState message="Loading report..." />
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : report ? (
            <ReportViewer report={report} />
          ) : null}
        </div>

        <div className="lg:col-span-1">
          <ReportHistory selectedReportId={selectedReportId ?? undefined} onSelect={setSelectedReportId} />
        </div>
      </div>
    </div>
  );
}
