import { cn } from '../../lib/utils';

const TYPE_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  manufacturer: { label: 'Производитель', bg: 'bg-purple-100', text: 'text-purple-700' },
  distributor: { label: 'Дистрибьютор', bg: 'bg-blue-100', text: 'text-blue-700' },
  wholesaler: { label: 'Оптовик', bg: 'bg-slate-100', text: 'text-slate-700' },
  retail: { label: 'Розница', bg: 'bg-green-100', text: 'text-green-700' },
  unknown: { label: 'Неизвестно', bg: 'bg-slate-100', text: 'text-slate-400' },
};

interface TypeBadgeProps {
  type: string;
  size?: 'sm' | 'md';
  className?: string;
}

export function TypeBadge({ type, size = 'md', className }: TypeBadgeProps) {
  const config = TYPE_CONFIG[type] || TYPE_CONFIG.unknown;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium',
        config.bg,
        config.text,
        size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1',
        className
      )}
    >
      {config.label}
    </span>
  );
}