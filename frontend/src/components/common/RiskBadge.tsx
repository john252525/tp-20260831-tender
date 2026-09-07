import { ShieldCheck, ShieldAlert, ShieldX, type LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

interface RiskConfig {
  label: string;
  bg: string;
  text: string;
  icon: LucideIcon;
}

const RISK_CONFIG: Record<string, RiskConfig> = {
  LOW: { label: 'LOW', bg: 'bg-green-100', text: 'text-green-700', icon: ShieldCheck },
  MEDIUM: { label: 'MEDIUM', bg: 'bg-yellow-100', text: 'text-yellow-700', icon: ShieldAlert },
  HIGH: { label: 'HIGH', bg: 'bg-red-100', text: 'text-red-700', icon: ShieldX },
};

interface RiskBadgeProps {
  level: string;
  size?: 'sm' | 'md';
  className?: string;
}

export function RiskBadge({ level, size = 'md', className }: RiskBadgeProps) {
  const config = RISK_CONFIG[level] || RISK_CONFIG.LOW;
  const Icon = config.icon;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-semibold',
        config.bg,
        config.text,
        size === 'sm' ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1',
        className
      )}
    >
      <Icon className={size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5'} aria-hidden="true" />
      {config.label}
    </span>
  );
}