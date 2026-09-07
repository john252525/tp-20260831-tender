import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  ScrollText,
  RefreshCw,
  Search,
  Circle,
  UserPlus,
  Inbox,
  MessagesSquare,
  CheckCircle2,
  AlertCircle,
  type LucideIcon,
} from 'lucide-react';
import { tendersApi, type TenderTimelineEvent } from '../api/tenders';
import { StatusBadge } from '../components/common/StatusBadge';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
import { formatDateTime, formatRelativeTime } from '../lib/formatters';
import { cn } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

const EVENT_TYPE_CONFIG: Record<string, { label: string; icon: LucideIcon; bg: string; text: string }> = {
  STATUS_CHANGE: { label: 'Смена статуса', icon: Circle, bg: 'bg-blue-100', text: 'text-blue-700' },
  SUPPLIER_ADDED: { label: 'Поставщик добавлен', icon: UserPlus, bg: 'bg-purple-100', text: 'text-purple-700' },
  CP_RECEIVED: { label: 'КП получено', icon: Inbox, bg: 'bg-green-100', text: 'text-green-700' },
  NEGOTIATION_STEP: { label: 'Переговоры', icon: MessagesSquare, bg: 'bg-yellow-100', text: 'text-yellow-700' },
  DECISION: { label: 'Решение', icon: CheckCircle2, bg: 'bg-green-100', text: 'text-green-700' },
  ERROR: { label: 'Ошибка', icon: AlertCircle, bg: 'bg-red-100', text: 'text-red-700' },
};
const EVENT_TYPES = ['STATUS_CHANGE', 'SUPPLIER_ADDED', 'CP_RECEIVED', 'NEGOTIATION_STEP', 'DECISION', 'ERROR'];

export function LogsPage() {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('all');

  const logsQuery = useQuery({
    queryKey: ['logs', 'timeline'],
    queryFn: async () => {
      const tenders = await tendersApi.list({ per_page: 50, sort_by: 'updated_at', sort_order: 'desc' });
      const tenderList = tenders.data || [];
      const allEvents: (TenderTimelineEvent & { tender_id: string; tender_title: string })[] = [];
      for (const tender of tenderList) {
        try {
          const timeline = await tendersApi.timeline(tender.id);
          timeline.forEach((event) => allEvents.push({ ...event, tender_id: tender.id, tender_title: tender.title }));
        } catch {}
      }
      allEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      return allEvents;
    },
  });

  const filteredEvents = useMemo(() => {
    const events = logsQuery.data || [];
    return events.filter((event) => {
      const matchesSearch = !searchText.trim() || event.description?.toLowerCase().includes(searchText.toLowerCase()) || event.tender_title?.toLowerCase().includes(searchText.toLowerCase());
      const matchesType = eventTypeFilter === 'all' || event.event_type === eventTypeFilter;
      return matchesSearch && matchesType;
    });
  }, [logsQuery.data, searchText, eventTypeFilter]);

  return (
    <div>
      <PageHeader title="Журнал" description="Хронология действий системы" actions={<Button variant="outline" size="sm" onClick={() => logsQuery.refetch()}><RefreshCw className="h-3.5 w-3.5 mr-1.5" />Обновить</Button>} />
      <div className="rounded-lg border border-slate-200 p-4 mb-6 bg-white">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label className="text-xs text-slate-500">Поиск</Label>
            <div className="relative mt-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input placeholder="Описание или название тендера" value={searchText} onChange={(e) => setSearchText(e.target.value)} className="pl-9" />
            </div>
          </div>
          <div>
            <Label className="text-xs text-slate-500">Тип события</Label>
            <Select value={eventTypeFilter} onValueChange={setEventTypeFilter}>
              <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все</SelectItem>
                {EVENT_TYPES.map((type) => <SelectItem key={type} value={type}>{EVENT_TYPE_CONFIG[type]?.label || type}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
      {logsQuery.isLoading ? (
        <LoadingSkeleton rows={10} cols={1} type="card" />
      ) : logsQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить журнал" onRetry={() => logsQuery.refetch()} />
      ) : filteredEvents.length === 0 ? (
        <EmptyState icon={ScrollText} title="Событий нет" description="Журнал будет заполняться по мере работы системы" />
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden bg-white">
          <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
            {filteredEvents.map((event, index) => {
              const config = EVENT_TYPE_CONFIG[event.event_type] || EVENT_TYPE_CONFIG.STATUS_CHANGE;
              const Icon = config.icon;
              return (
                <div key={index} className="p-3 hover:bg-slate-50">
                  <div className="flex items-start gap-3">
                    <div className={cn('h-8 w-8 rounded-lg flex items-center justify-center flex-shrink-0', config.bg)}>
                      <Icon className={cn('h-4 w-4', config.text)} aria-hidden="true" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={cn('text-xs font-medium rounded-full px-2 py-0.5', config.bg, config.text)}>{config.label}</span>
                        <span className="text-xs text-slate-400">{formatDateTime(event.timestamp)}</span>
                        <span className="text-xs text-slate-400">({formatRelativeTime(event.timestamp)})</span>
                      </div>
                      <p className="text-sm text-slate-900 mt-1">{event.description}</p>
                      {event.tender_title && (
                        <button onClick={() => navigate(`/tenders/${event.tender_id}`)} className="text-xs text-blue-600 hover:underline mt-1">
                          {event.tender_title}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}