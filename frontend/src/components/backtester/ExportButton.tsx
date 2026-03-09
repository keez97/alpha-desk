import { useExportBacktest } from '../../hooks/useBacktester';

interface ExportButtonProps {
  backtestId: number;
  onExport?: () => void;
}

export function ExportButton({ backtestId, onExport }: ExportButtonProps) {
  const { data: exportData } = useExportBacktest(backtestId);

  const handleDownload = () => {
    if (!exportData) return;

    const json = JSON.stringify(exportData, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backtest-${backtestId}-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    if (onExport) {
      onExport();
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={!exportData}
      className="px-3 py-1 rounded text-xs font-medium uppercase tracking-wider border border-neutral-800 text-neutral-400 hover:text-neutral-200 hover:border-neutral-700 disabled:opacity-50 transition-colors"
    >
      Export JSON
    </button>
  );
}
