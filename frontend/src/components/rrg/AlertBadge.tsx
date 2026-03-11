import type { RotationAlert } from '../../hooks/useRotationAlerts';
import { useAlertSummary } from '../../hooks/useRotationAlerts';

interface AlertBadgeProps {
  alerts?: RotationAlert[] | undefined;
  isLoading?: boolean;
}

export function AlertBadge({ alerts, isLoading }: AlertBadgeProps) {
  const summary = useAlertSummary(alerts);

  if (isLoading) {
    return (
      <div className="inline-flex items-center justify-center w-6 h-6 bg-neutral-700 rounded-full text-xs font-medium text-neutral-400">
        --
      </div>
    );
  }

  if (summary.total === 0) {
    return (
      <div className="inline-flex items-center justify-center w-6 h-6 bg-neutral-800 rounded-full text-xs font-medium text-neutral-500">
        0
      </div>
    );
  }

  const bgColor =
    summary.highestSeverity === 'critical'
      ? 'bg-red-500'
      : summary.highestSeverity === 'warning'
      ? 'bg-amber-500'
      : 'bg-blue-500';

  return (
    <div className={`inline-flex items-center justify-center w-6 h-6 ${bgColor} rounded-full text-xs font-bold text-white`}>
      {summary.total}
    </div>
  );
}
