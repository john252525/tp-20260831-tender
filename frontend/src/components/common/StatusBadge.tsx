import {
  Circle,
  Download,
  CheckCircle2,
  Loader2,
  Filter,
  HelpCircle,
  XCircle,
  Calculator,
  Gauge,
  Clock,
  Search,
  Users,
  UserX,
  Send,
  Inbox,
  MessagesSquare,
  ClipboardCheck,
  Check,
  X,
  AlertCircle,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface StatusConfig {
  label: string;
  bg: string;
  text: string;
  icon?: LucideIcon;
  pulse?: boolean;
}

const STATUS_CONFIG: Record<string, StatusConfig> = {
  NEW: { label: 'Новый', bg: 'bg-slate-100', text: 'text-slate-700', icon: Circle },
  DOCUMENTS_LOADING: { label: 'Загрузка документов', bg: 'bg-blue-100', text: 'text-blue-700', icon: Download, pulse: true },
  DOCUMENTS_LOADED: { label: 'Документы загружены', bg: 'bg-blue-100', text: 'text-blue-700', icon: CheckCircle2 },
  PROCESSING: { label: 'Обработка', bg: 'bg-blue-100', text: 'text-blue-700', icon: Loader2, pulse: true },
  SEMANTIC_FILTERING: { label: 'Фильтрация', bg: 'bg-blue-100', text: 'text-blue-700', icon: Filter, pulse: true },
  RELEVANT: { label: 'Релевантный', bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2 },
  UNCERTAIN: { label: 'Под вопросом', bg: 'bg-yellow-100', text: 'text-yellow-700', icon: HelpCircle },
  NOT_RELEVANT: { label: 'Нерелевантный', bg: 'bg-slate-100', text: 'text-slate-500', icon: XCircle },
  SCORING: { label: 'Скоринг', bg: 'bg-blue-100', text: 'text-blue-700', icon: Calculator, pulse: true },
  SCORED: { label: 'Оценён', bg: 'bg-blue-100', text: 'text-blue-700', icon: Gauge },
  AWAITING_SUPPLIER_SEARCH: { label: 'Ожидание поиска', bg: 'bg-slate-100', text: 'text-slate-700', icon: Clock },
  SUPPLIER_SEARCH_IN_PROGRESS: { label: 'Поиск поставщиков', bg: 'bg-blue-100', text: 'text-blue-700', icon: Search, pulse: true },
  SUPPLIERS_FOUND: { label: 'Поставщики найдены', bg: 'bg-green-100', text: 'text-green-700', icon: Users },
  NO_SUPPLIERS_FOUND: { label: 'Нет поставщиков', bg: 'bg-red-100', text: 'text-red-700', icon: UserX },
  AWAITING_CP: { label: 'Ожидание КП', bg: 'bg-slate-100', text: 'text-slate-700', icon: Clock },
  CP_REQUESTED: { label: 'КП запрошены', bg: 'bg-blue-100', text: 'text-blue-700', icon: Send },
  CP_PARTIALLY_RECEIVED: { label: 'КП частично', bg: 'bg-yellow-100', text: 'text-yellow-700', icon: Inbox },
  CP_FULLY_RECEIVED: { label: 'КП получены', bg: 'bg-green-100', text: 'text-green-700', icon: Inbox },
  NEGOTIATING: { label: 'Переговоры', bg: 'bg-yellow-100', text: 'text-yellow-700', icon: MessagesSquare, pulse: true },
  READY_FOR_DECISION: { label: 'Готов к решению', bg: 'bg-purple-100', text: 'text-purple-700', icon: ClipboardCheck },
  APPROVED: { label: 'Одобрен', bg: 'bg-green-600', text: 'text-white', icon: Check },
  REJECTED: { label: 'Отклонён', bg: 'bg-red-600', text: 'text-white', icon: X },
  ERROR: { label: 'Ошибка', bg: 'bg-red-100', text: 'text-red-700', icon: AlertCircle },
};

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function StatusBadge({ status, size = 'md', className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] || {
    label: status,
    bg: 'bg-slate-100',
    text: 'text-slate-700',
  };
  const Icon = config.icon;
  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2',
  };
  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full font-medium whitespace-nowrap',
        config.bg,
        config.text,
        sizeClasses[size],
        className
      )}
    >
      {Icon && (
        <Icon
          className={cn(
            iconSizes[size],
            config.pulse && 'animate-spin'
          )}
          aria-hidden="true"
        />
      )}
      {config.label}
    </span>
  );
}