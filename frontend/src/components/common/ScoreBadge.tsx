import { cn } from '../../lib/utils';

interface ScoreBadgeProps {
  score: number | null;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

function getScoreColor(score: number): string {
  if (score >= 70) return 'bg-green-100 text-green-700';
  if (score >= 40) return 'bg-yellow-100 text-yellow-700';
  return 'bg-red-100 text-red-700';
}

export function ScoreBadge({ score, size = 'md', className }: ScoreBadgeProps) {
  if (score === null || score === undefined) {
    return <span className="text-slate-400 text-xs">—</span>;
  }
  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5 font-semibold',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-semibold',
        getScoreColor(score),
        sizeClasses[size],
        className
      )}
    >
      {score.toFixed(1)}
    </span>
  );
}