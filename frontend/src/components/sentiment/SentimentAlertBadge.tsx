import { SentimentAlert } from '../../lib/api';
import { classNames } from '../../lib/utils';

interface SentimentAlertBadgeProps {
  alert: SentimentAlert;
}

export function SentimentAlertBadge({ alert }: SentimentAlertBadgeProps) {
  const getAlertStyles = (alertType: string) => {
    const baseClasses = 'text-[10px] font-semibold px-2 py-1 rounded flex items-center gap-1 whitespace-nowrap';

    if (alertType === 'contrarian_bullish') {
      return classNames(baseClasses, 'border border-emerald-600 text-emerald-400');
    } else if (alertType === 'contrarian_bearish') {
      return classNames(baseClasses, 'border border-red-600 text-red-400');
    } else if (alertType === 'velocity_spike') {
      return classNames(baseClasses, 'border border-yellow-600 text-yellow-400');
    }
    return classNames(baseClasses, 'border border-neutral-600 text-neutral-400');
  };

  const getAlertLabel = (alertType: string) => {
    if (alertType === 'contrarian_bullish') {
      return 'CONTRARIAN ↑';
    } else if (alertType === 'contrarian_bearish') {
      return 'CONTRARIAN ↓';
    } else if (alertType === 'velocity_spike') {
      return 'VELOCITY SPIKE';
    }
    return alertType.toUpperCase();
  };

  return (
    <div className={getAlertStyles(alert.alert_type)}>
      {getAlertLabel(alert.alert_type)}
    </div>
  );
}
