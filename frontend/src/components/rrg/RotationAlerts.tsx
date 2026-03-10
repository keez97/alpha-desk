'use client';

import type { RotationAlert } from '../../hooks/useRotationAlerts';
import { useRotationAlerts, useScanForAlerts } from '../../hooks/useRotationAlerts';

interface RotationAlertsProps {
  benchmark?: string;
  weeks?: number;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-500',
  warning: 'text-amber-500',
  info: 'text-blue-500',
};

const SEVERITY_BG: Record<string, string> = {
  critical: 'border-l-red-500 bg-red-500/5',
  warning: 'border-l-amber-500 bg-amber-500/5',
  info: 'border-l-blue-500 bg-blue-500/5',
};

const ALERT_TYPE_BADGE: Record<string, { bg: string; text: string }> = {
  quadrant_change: { bg: 'bg-purple-500/10', text: 'text-purple-400' },
  momentum_reversal: { bg: 'bg-orange-500/10', text: 'text-orange-400' },
  breakout: { bg: 'bg-green-500/10', text: 'text-green-400' },
  breakdown: { bg: 'bg-red-500/10', text: 'text-red-400' },
};

function SeverityIcon({ severity }: { severity: string }) {
  if (severity === 'critical') {
    return (
      <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
    );
  }
  if (severity === 'warning') {
    return (
      <div className="w-2 h-2 rounded-full bg-amber-500" />
    );
  }
  return (
    <div className="w-2 h-2 rounded-full bg-blue-500" />
  );
}

function AlertTypeTag({ alertType }: { alertType: string }) {
  const style = ALERT_TYPE_BADGE[alertType] || {
    bg: 'bg-neutral-700/50',
    text: 'text-neutral-400',
  };
  const label = alertType
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}>
      {label}
    </span>
  );
}

function AlertCard({ alert }: { alert: RotationAlert }) {
  return (
    <div
      className={`border-l-2 px-4 py-3 rounded text-xs space-y-1 ${
        SEVERITY_BG[alert.severity]
      }`}
    >
      <div className="flex items-center gap-2">
        <SeverityIcon severity={alert.severity} />
        <span className="font-semibold text-neutral-100">
          {alert.ticker}
        </span>
        <span className="text-neutral-400">•</span>
        <span className="text-neutral-300">{alert.sector}</span>
        <AlertTypeTag alertType={alert.alertType} />
      </div>

      <p className="text-neutral-300">{alert.description}</p>

      <div className="flex items-center gap-3 pt-1 text-neutral-400">
        <span>RS-Ratio: {alert.rsRatio.toFixed(2)}</span>
        <span>RS-Mom: {alert.rsMomentum.toFixed(2)}</span>
        <span className="text-neutral-500">
          {alert.createdAt && !isNaN(new Date(alert.createdAt).getTime())
            ? new Date(alert.createdAt).toLocaleTimeString()
            : 'Just now'}
        </span>
      </div>
    </div>
  );
}

export function RotationAlerts({
  benchmark = 'SPY',
  weeks = 10,
}: RotationAlertsProps) {
  const { data, isLoading, error } = useRotationAlerts(benchmark, weeks);
  const scanMutation = useScanForAlerts();

  const alerts = data?.alerts || [];

  // Sort by severity: critical > warning > info
  const sortedAlerts = [...alerts].sort((a, b) => {
    const severityOrder = { critical: 0, warning: 1, info: 2 };
    return severityOrder[a.severity] - severityOrder[b.severity];
  });

  const handleScan = () => {
    scanMutation.mutate({ benchmark, weeks });
  };

  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded-lg p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-100">
          Rotation Alerts
        </h3>
        <button
          onClick={handleScan}
          disabled={isLoading || scanMutation.isPending}
          className="px-3 py-1 text-xs font-medium bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-700 disabled:text-neutral-500 text-white rounded transition-colors"
        >
          {scanMutation.isPending ? 'Scanning...' : 'Scan Now'}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400">
          Failed to load alerts
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 bg-neutral-800 rounded animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && sortedAlerts.length === 0 && (
        <div className="p-4 text-center text-neutral-400 text-xs">
          No rotation alerts detected
        </div>
      )}

      {/* Alerts list */}
      {!isLoading && sortedAlerts.length > 0 && (
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {sortedAlerts.map((alert, idx) => (
            <AlertCard key={`${alert.ticker}-${alert.alertType}-${idx}`} alert={alert} />
          ))}
        </div>
      )}

      {/* Footer: alert count summary */}
      {!isLoading && sortedAlerts.length > 0 && (
        <div className="pt-2 border-t border-neutral-800 flex gap-4 text-xs text-neutral-400">
          <span>
            Critical:{' '}
            <span className="text-red-500 font-semibold">
              {sortedAlerts.filter((a) => a.severity === 'critical').length}
            </span>
          </span>
          <span>
            Warning:{' '}
            <span className="text-amber-500 font-semibold">
              {sortedAlerts.filter((a) => a.severity === 'warning').length}
            </span>
          </span>
          <span>
            Info:{' '}
            <span className="text-blue-500 font-semibold">
              {sortedAlerts.filter((a) => a.severity === 'info').length}
            </span>
          </span>
        </div>
      )}
    </div>
  );
}
