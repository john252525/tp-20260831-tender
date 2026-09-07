import { cn } from '../../lib/utils';

interface ProgressBarProps {
  value: number;
  size?: 'sm' | 'md' | 'lg';
  color?: 'auto' | 'blue' | 'green' | 'red' | 'yellow';
  showLabel?: boolean;
  animate?: boolean;
  className?: string;
}

function getColor(value: number, color?: string): string {
  if (color && color !== 'auto') {
    switch (color) {
      case 'blue': return 'bg-blue-600';
      case 'green': return 'bg-green-600';
      case 'red': return 'bg-red-600';
      case 'yellow': return 'bg-yellow-600';
      default: return 'bg-blue-600';
    }
  }
  if (value >= 70) return 'bg-green-600';
  if (value >= 25) return 'bg-blue-600';
  return 'bg-red-600';
}

export function ProgressBar({ value, size = 'md', color = 'auto', showLabel = false, animate = true, className }: ProgressBarProps) {
  const heights = { sm: 'h-1.5', md: 'h-2', lg: 'h-3' };
  const clampedValue = Math.min(100, Math.max(0, value));
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className={cn('flex-1 rounded-full bg-slate-200 overflow-hidden', heights[size])}
        role="progressbar"
        aria-valuenow={clampedValue}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={cn(
            'rounded-full h-full',
            getColor(clampedValue, color),
            animate && 'transition-all duration-500'
          )}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-slate-600 whitespace-nowrap">
          {clampedValue.toFixed(0)}%
        </span>
      )}
    </div>
  );
}