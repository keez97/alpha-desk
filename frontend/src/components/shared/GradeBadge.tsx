interface GradeBadgeProps {
  grade: string;
  size?: 'sm' | 'md' | 'lg';
}

const gradeColors: Record<string, string> = {
  'A+': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  'A': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  'A-': 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  'B+': 'bg-neutral-500/10 text-neutral-300 border-neutral-500/20',
  'B': 'bg-neutral-500/10 text-neutral-300 border-neutral-500/20',
  'B-': 'bg-neutral-500/10 text-neutral-300 border-neutral-500/20',
  'C+': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  'C': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  'C-': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  'D': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  'F': 'bg-red-500/10 text-red-400 border-red-500/20',
};

const sizeClasses = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

export function GradeBadge({ grade, size = 'md' }: GradeBadgeProps) {
  const colorClass = gradeColors[grade] || 'bg-neutral-500/10 text-neutral-400 border-neutral-500/20';

  return (
    <span className={`inline-block rounded border font-bold font-mono ${colorClass} ${sizeClasses[size]}`}>
      {grade}
    </span>
  );
}
