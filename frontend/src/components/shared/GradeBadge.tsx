interface GradeBadgeProps {
  grade: string;
  size?: 'sm' | 'md' | 'lg';
}

const gradeColors: Record<string, string> = {
  'A+': 'bg-green-500/20 text-green-400 border-green-500/30',
  'A': 'bg-green-500/20 text-green-400 border-green-500/30',
  'A-': 'bg-green-500/20 text-green-400 border-green-500/30',
  'B+': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  'B': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  'B-': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  'C+': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'C': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'C-': 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  'D': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  'F': 'bg-red-500/20 text-red-400 border-red-500/30',
};

const sizeClasses = {
  sm: 'px-2 py-1 text-xs',
  md: 'px-3 py-1.5 text-sm',
  lg: 'px-4 py-2 text-lg',
};

export function GradeBadge({ grade, size = 'md' }: GradeBadgeProps) {
  const colorClass = gradeColors[grade] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';

  return (
    <span className={`inline-block rounded-lg border font-bold font-mono ${colorClass} ${sizeClasses[size]}`}>
      {grade}
    </span>
  );
}
