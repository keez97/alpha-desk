interface GradeBadgeProps {
  grade: string;
  size?: 'sm' | 'md' | 'lg';
}

export function GradeBadge({ grade, size = 'md' }: GradeBadgeProps) {
  const sizeClasses = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
    lg: 'px-4 py-2 text-lg',
  };

  const gradeUpper = grade.toUpperCase();

  const colorClasses = {
    A: 'bg-green-500/20 text-green-400 border border-green-500/30',
    B: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    C: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
    D: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
    F: 'bg-red-500/20 text-red-400 border border-red-500/30',
  } as const;

  const color = colorClasses[gradeUpper as keyof typeof colorClasses] || colorClasses.F;

  return (
    <span className={`inline-block rounded font-bold font-mono ${sizeClasses[size]} ${color}`}>
      {gradeUpper}
    </span>
  );
}
