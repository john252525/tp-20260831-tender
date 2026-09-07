import { cn } from '../../lib/utils';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: LucideIcon;
  iconBg?: string;
  iconText?: string;
  description?: string;
  onClick?: () => void;
  className?: string;
}

export function StatCard({ title, value, icon: Icon, iconBg, iconText, description, onClick, className }: StatCardProps) {
  const content = (
    <>
      {Icon && (
        <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg', iconBg || 'bg-slate-100', iconText || 'text-slate-600')}>
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
      )}
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <p className="text-2xl font-semibold text-slate-900">{value}</p>
        {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
      </div>
    </>
  );

  if (onClick) {
    return (
      <button
        onClick={onClick}
        className={cn(
          'flex items-center gap-4 rounded-lg border border-slate-200 bg-white p-4 cursor-pointer hover:border-slate-300 transition-colors text-left w-full',
          className
        )}
      >
        {content}
      </button>
    );
  }

  return (
    <div className={cn('flex items-center gap-4 rounded-lg border border-slate-200 bg-white p-4', className)}>
      {content}
    </div>
  );
}