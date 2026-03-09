import type { Report } from '../../lib/api';
import { ReportSection } from './ReportSection';
import { Timestamp } from '../shared/Timestamp';

interface ReportViewerProps {
  report: Report;
}

export function ReportViewer({ report }: ReportViewerProps) {
  return (
    <div className="space-y-2">
      <div className="px-1">
        <span className="text-sm font-medium text-neutral-200">{report.title}</span>
        <div className="mt-0.5">
          <Timestamp date={report.date} label="Report Date" />
        </div>
      </div>

      {report.sections.map((section, idx) => (
        <ReportSection key={idx} title={section.title} defaultOpen={idx === 0}>
          <div className="space-y-3">
            <p className="whitespace-pre-wrap text-xs text-neutral-400 leading-relaxed">{section.content}</p>
            {section.tables && section.tables.length > 0 && (
              <div>
                {section.tables.map((table: any, tableIdx: number) => (
                  <div key={tableIdx} className="mt-2">
                    {table.columns && table.rows && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs border-collapse">
                          <thead>
                            <tr className="border-b border-neutral-800">
                              {table.columns.map((col: string, idx: number) => (
                                <th key={idx} className="px-3 py-1.5 text-left text-[10px] text-neutral-500 uppercase tracking-wider font-medium">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {table.rows.map((row: any, ridx: number) => (
                              <tr key={ridx} className="border-b border-neutral-900 hover:bg-neutral-900/50">
                                {row.map((cell: any, cidx: number) => (
                                  <td key={cidx} className="px-3 py-1.5 text-neutral-300 font-mono">
                                    {cell}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </ReportSection>
      ))}
    </div>
  );
}
