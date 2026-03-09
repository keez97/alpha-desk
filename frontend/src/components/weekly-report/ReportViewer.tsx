import type { Report } from '../../lib/api';
import { ReportSection } from './ReportSection';
import { Timestamp } from '../shared/Timestamp';

interface ReportViewerProps {
  report: Report;
}

export function ReportViewer({ report }: ReportViewerProps) {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="mb-2 text-2xl font-bold text-white">{report.title}</h1>
        <Timestamp date={report.date} label="Report Date" />
      </div>

      {report.sections.map((section, idx) => (
        <ReportSection key={idx} title={section.title} defaultOpen={idx === 0}>
          <div className="space-y-4">
            <p className="whitespace-pre-wrap text-sm text-gray-300">{section.content}</p>
            {section.tables && section.tables.length > 0 && (
              <div className="mt-4">
                {section.tables.map((table: any, tableIdx: number) => (
                  <div key={tableIdx} className="mt-4">
                    {table.columns && table.rows && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm border-collapse">
                          <thead>
                            <tr className="border-b border-gray-700 bg-gray-700/20">
                              {table.columns.map((col: string, idx: number) => (
                                <th key={idx} className="px-4 py-2 text-left text-gray-300 font-semibold">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {table.rows.map((row: any, ridx: number) => (
                              <tr key={ridx} className="border-b border-gray-800 hover:bg-gray-800/30">
                                {row.map((cell: any, cidx: number) => (
                                  <td key={cidx} className="px-4 py-2 text-gray-300 font-mono">
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
