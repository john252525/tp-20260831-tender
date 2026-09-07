import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  FolderTree,
  RadioTower,
  Mail,
  Gauge,
  MessagesSquare,
  Webhook,
  ChevronRight,
  RefreshCw,
  type LucideIcon,
} from 'lucide-react';
import { categoriesApi } from '../api/categories';
import { tenderSourcesApi } from '../api/tenderSources';
import { webhooksApi } from '../api/webhooks';
import { settingsApi } from '../api/settings';
import { PageHeader } from '../components/common/PageHeader';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { Button } from '../components/ui/button';
import { cn } from '../lib/utils';

function ModuleCard({
  icon: Icon,
  title,
  description,
  status,
  iconBg,
  iconText,
  onClick,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  status: string;
  iconBg: string;
  iconText: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="rounded-lg border border-slate-200 bg-white p-5 text-left hover:border-blue-200 hover:shadow-md transition-all cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-4">
        <div className={cn('h-12 w-12 rounded-lg flex items-center justify-center', iconBg)}>
          <Icon className={cn('h-6 w-6', iconText)} aria-hidden="true" />
        </div>
        <ChevronRight className="h-5 w-5 text-slate-300 group-hover:text-blue-500 transition-colors" aria-hidden="true" />
      </div>
      <h3 className="text-base font-semibold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 mb-3">{description}</p>
      <div className="inline-flex items-center gap-1.5 rounded-full bg-slate-50 border border-slate-200 px-2.5 py-1">
        <span className={cn('h-1.5 w-1.5 rounded-full', status === 'active' ? 'bg-green-500' : 'bg-slate-300')} />
        <span className="text-xs font-medium text-slate-600">{status}</span>
      </div>
    </button>
  );
}

export function AutomationPage() {
  const navigate = useNavigate();

  const categoriesQuery = useQuery({
    queryKey: ['categories', 'count'],
    queryFn: () => categoriesApi.list({ per_page: 1, is_active: true }),
  });
  const sourcesQuery = useQuery({
    queryKey: ['tender-sources', 'count'],
    queryFn: () => tenderSourcesApi.list(),
  });
  const webhooksQuery = useQuery({
    queryKey: ['webhooks', 'count'],
    queryFn: () => webhooksApi.list(),
  });
  const scoringQuery = useQuery({
    queryKey: ['settings', 'scoring'],
    queryFn: () => settingsApi.getSection('scoring'),
  });
  const negotiationQuery = useQuery({
    queryKey: ['settings', 'communication'],
    queryFn: () => settingsApi.getSection('communication'),
  });

  const isLoading =
    categoriesQuery.isLoading ||
    sourcesQuery.isLoading ||
    webhooksQuery.isLoading ||
    scoringQuery.isLoading ||
    negotiationQuery.isLoading;

  const isError =
    categoriesQuery.isError ||
    sourcesQuery.isError ||
    webhooksQuery.isError ||
    scoringQuery.isError ||
    negotiationQuery.isError;

  const categoriesCount = categoriesQuery.data?.length || 0;
  const sourcesCount = sourcesQuery.data?.filter((s: any) => s.is_active).length || 0;
  const webhooksCount = webhooksQuery.data?.filter((w: any) => w.is_active).length || 0;
  const minScore = scoringQuery.data?.min_total_score || '—';
  const maxCycles = negotiationQuery.data?.max_clarification_cycles || '—';

  const modules = [
    { icon: FolderTree, title: 'Категории', description: 'Профильные категории товаров для семантического поиска', status: `${categoriesCount} активных`, iconBg: 'bg-green-100', iconText: 'text-green-700', onClick: () => navigate('/automation/categories') },
    { icon: RadioTower, title: 'Источники', description: 'API-агрегаторы для получения тендеров', status: `${sourcesCount} подключено`, iconBg: 'bg-blue-100', iconText: 'text-blue-700', onClick: () => navigate('/automation/sources') },
    { icon: Mail, title: 'Шаблоны писем', description: 'Шаблоны для автоматической коммуникации с поставщиками', status: '4 шаблона', iconBg: 'bg-purple-100', iconText: 'text-purple-700', onClick: () => navigate('/automation/templates') },
    { icon: Gauge, title: 'Скоринг', description: 'Параметры оценки привлекательности тендеров', status: `Порог: ${minScore}`, iconBg: 'bg-yellow-100', iconText: 'text-yellow-700', onClick: () => navigate('/automation/scoring') },
    { icon: MessagesSquare, title: 'Переговоры', description: 'Стратегия автоматических переговоров', status: `${maxCycles} циклов`, iconBg: 'bg-orange-100', iconText: 'text-orange-700', onClick: () => navigate('/automation/negotiation') },
    { icon: Webhook, title: 'Вебхуки', description: 'Интеграции с внешними системами', status: `${webhooksCount} активных`, iconBg: 'bg-slate-100', iconText: 'text-slate-600', onClick: () => navigate('/automation/webhooks') },
  ];

  const handleRefreshAll = () => {
    categoriesQuery.refetch();
    sourcesQuery.refetch();
    webhooksQuery.refetch();
    scoringQuery.refetch();
    negotiationQuery.refetch();
  };

  return (
    <div>
      <PageHeader
        title="Автопилот"
        description="Настройка автоматической работы системы"
        actions={
          <Button variant="outline" size="sm" onClick={handleRefreshAll}>
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Обновить
          </Button>
        }
      />
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <LoadingSkeleton key={i} rows={1} cols={1} type="card" />)}
        </div>
      ) : isError ? (
        <ErrorAlert message="Не удалось загрузить данные" onRetry={handleRefreshAll} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {modules.map((module) => (
            <ModuleCard key={module.title} {...module} />
          ))}
        </div>
      )}
    </div>
  );
}