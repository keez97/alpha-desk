import { classNames } from '../../lib/utils';

interface SeverityBadgeProps {
  score: number;
  showLabel?: boolean;
}

export function SeverityBadge({ score, showLabel = false }: SeverityBadgeProps) {
  const level = Math.ceil(score);

  const getColor = (level: number) => {
    switch (level) {
      case 1:
        return 'text-neutral-600';
      case 2:
        return 'text-neutral-400';
      case 3:
        return 'text-yellow-500';
      case 4:
        return 'text-orange-500';
      case 5:
        return 'text-red-500';
      default:
        return 'text-neutral-500';
    }
  };

  const getLabel = (level: number) => {
    switch (level) {
      case 1:
        return 'Minimal';
      case 2:
        return 'Low';
      case 3:
        return 'Medium';
      case 4:
        return 'High';
      case 5:
        return 'Critical';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="flex items-center gap-1">
      <div className={classNames('w-2 h-2 rounded-full', getColor(level))} style={{ backgroundColor: 'currentColor' }} />
      {showLabel && <span className={classNames('text-[10px] font-medium', getColor(level))}>{getLabel(level)}</span>}
    </div>
  );
}
