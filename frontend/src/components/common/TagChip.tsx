import { cn } from '../../lib/utils';

interface TagChipProps {
  label: string;
  className?: string;
  onClick?: () => void;
}

export function TagChip({ label, className, onClick }: TagChipProps) {
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className={cn(
          'inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer',
          className
        )}
      >
        {label}
      </button>
    );
  }
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700',
        className
      )}
    >
      {label}
    </span>
  );
}