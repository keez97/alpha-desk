import { Timestamp } from '../shared/Timestamp';
import type { PollingStatus } from '../../lib/api';

interface ScanButtonProps {
  onScan: () => void;
  isScanning?: boolean;
  pollingStatus?: PollingStatus | null;
}

export function ScanButton({ onScan, isScanning = false, pollingStatus }: ScanButtonProps) {
  return (
    <div className="space-y-2">
      <button
        onClick={onScan}
        disabled={isScanning}
        className="w-full px-3 py-2 rounded text-xs font-medium text-neutral-300 border border-neutral-800 bg-neutral-900 hover:text-neutral-100 hover:border-neutral-700 disabled:opacity-50 transition-colors"
      >
        {isScanning ? 'Scanning...' : 'Scan Now'}
      </button>

      {pollingStatus && (
        <div className="border border-neutral-800 rounded p-2 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-neutral-400 font-medium">Status</span>
            <span className={`text-[10px] font-medium uppercase ${pollingStatus.status === 'running' ? 'text-yellow-500' : 'text-neutral-400'}`}>
              {pollingStatus.status}
            </span>
          </div>
          {pollingStatus.last_run && <Timestamp date={pollingStatus.last_run} label="Last Scan" />}
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-neutral-500">Events Found</span>
            <span className="text-[10px] font-semibold text-neutral-300">{pollingStatus.events_found}</span>
          </div>
        </div>
      )}
    </div>
  );
}
