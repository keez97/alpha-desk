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
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Weekly Report</h1>
        <p className="text-gray-400">AI-powered market analysis and insights</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        <div className="lg:col-span-3">
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
