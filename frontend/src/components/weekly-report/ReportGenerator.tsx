import { useGenerateWeeklyReport } from '../../hooks/useWeeklyReport';
import { LoadingState } from '../shared/LoadingState';

export function ReportGenerator() {
  const { generate, sections, isGenerating, error } = useGenerateWeeklyReport();

  return (
    <div className="space-y-6">
      {!isGenerating && sections.length === 0 && (
        <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-8 text-center">
          <h2 className="mb-4 text-2xl font-bold text-white">Generate Weekly Report</h2>
          <p className="mb-6 text-gray-400">
            Create a comprehensive analysis of market drivers, sector trends, and investment opportunities.
          </p>
          <button
            onClick={() => generate()}
            className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Generate Report
          </button>
        </div>
      )}

      {isGenerating && sections.length === 0 && (
        <div className="rounded-lg border border-gray-700 bg-gray-800/30 p-8">
          <LoadingState message="Generating report..." />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-700 bg-red-500/10 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {sections.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Report Sections</h2>
            {isGenerating && (
              <div className="flex items-center space-x-2 text-sm text-gray-400">
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse"></div>
                <span>Generating...</span>
              </div>
            )}
          </div>

          {sections.map((section, idx) => (
            <div key={idx} className="rounded-lg border border-gray-700 bg-gray-800/30 p-4">
              <h3 className="mb-3 font-semibold text-white">{section.title}</h3>
              <p className="text-sm text-gray-300 whitespace-pre-wrap">{section.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
