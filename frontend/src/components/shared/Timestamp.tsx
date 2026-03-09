import { formatTimestamp } from '../../lib/utils';

interface TimestampProps {
  date: string;
  label?: string;
}

export function Timestamp({ date, label = 'Generated' }: TimestampProps) {
  return (
    <div className="flex items-center space-x-2 text-xs text-gray-500">
      <span>{label}:</span>
      <span className="font-mono">{formatTimestamp(date)}</span>
    </div>
  );
}
