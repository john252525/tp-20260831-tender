import { cn } from '../../lib/utils';

interface LoadingSkeletonProps {
  rows?: number;
  cols?: number;
  type?: 'table' | 'card' | 'form';
  className?: string;
}

export function LoadingSkeleton({ rows = 5, cols = 4, type = 'table', className }: LoadingSkeletonProps) {
  if (type === 'table') {
    return (
      <div className={cn('w-full space-y-3', className)} role="status" aria-label="Загрузка...">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex items-center gap-4 animate-pulse">
            {Array.from({ length: cols }).map((_, colIndex) => (
              <div
                key={colIndex}
                className="h-4 rounded bg-slate-200"
                style={{ flex: colIndex === 0 ? 2 : 1 }}
              />
            ))}
          </div>
        ))}
      </div>
    );
  }
  if (type === 'card') {
    return (
      <div className={cn('rounded-lg border border-slate-200 p-4 animate-pulse', className)} role="status" aria-label="Загрузка...">
        <div className="h-4 w-1/3 rounded bg-slate-200 mb-3" />
        <div className="space-y-2">
          <div className="h-3 rounded bg-slate-100" />
          <div className="h-3 rounded bg-slate-100" />
          <div className="h-3 w-2/3 rounded bg-slate-100" />
        </div>
      </div>
    );
  }
  return (
    <div className={cn('space-y-4 animate-pulse', className)} role="status" aria-label="Загрузка...">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-9 rounded-md bg-slate-100" />
      ))}
    </div>
  );
}