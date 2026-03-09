import { useGenerateWeeklyReport } from '../../hooks/useWeeklyReport';
import { LoadingState } from '../shared/LoadingState';

export function ReportGenerator() {
  const { generate, sections, isGenerating, error } = useGenerateWeeklyReport();

  return (
    <div className="space-y-3">
      {!isGenerating && sections.length === 0 && (
        <div className="border border-neutral-800 rounded p-6 text-center">
          <p className="text-xs text-neutral-500 mb-4">
            Generate a comprehensive analysis of market drivers, sector trends, and investment opportunities.
          </p>
          <button
            onClick={() => generate()}
            className="rounded px-4 py-1.5 text-xs font-medium text-neutral-300 border border-neutral-700 hover:border-neutral-600 hover:text-neutral-100 transition-colors"
          >
            Generate Report
          </button>
        </div>
      )}

      {isGenerating && sections.length === 0 && (
        <div className="border border-neutral-800 rounded p-6">
          <LoadingState message="Generating report..." />
        </div>
      )}

      {error && (
        <div className="border border-red-900/50 rounded px-3 py-2">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {sections.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-medium text-neutral-300">Report Sections</span>
            {isGenerating && (
              <div className="flex items-center gap-1.5 text-[10px] text-neutral-500">
                <div className="h-1.5 w-1.5 rounded-full bg-neutral-500 animate-pulse"></div>
                <span>Generating...</span>
              </div>
            )}
          </div>

          {sections.map((section, idx) => (
            <div key={idx} className="border border-neutral-800 rounded px-4 py-3">
              <h3 className="text-xs font-medium text-neutral-200 mb-2">{section.title}</h3>
              <p className="text-xs text-neutral-400 whitespace-pre-wrap leading-relaxed">{section.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
