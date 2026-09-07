import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  RefreshCw,
  Inbox,
  FileText,
  Building2,
  ClipboardCheck,
  Activity,
  ArrowRight,
  CheckCircle2,
  Gauge,
  Users,
  Search,
  Send,
  type LucideIcon,
} from 'lucide-react';
import { tendersApi, type TenderStats } from '../api/tenders';
import { tasksApi, type TaskStatus } from '../api/tasks';
import { decisionsApi, type DecisionListItem } from '../api/decisions';
import { StatusBadge } from '../components/common/StatusBadge';
import { RiskBadge } from '../components/common/RiskBadge';
import { ProgressBar } from '../components/common/ProgressBar';
import { ScoreBadge } from '../components/common/ScoreBadge';
import { StatCard } from '../components/common/StatCard';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
import { formatMoney, formatRelativeTime } from '../lib/formatters';
import { cn } from '../lib/utils';

interface PipelineStage {
  key: string;
  label: string;
  icon: LucideIcon;
  bg: string;
  statuses: string[];
  count: number;
}

function calculateStages(stats: TenderStats | undefined): PipelineStage[] {
  const byStatus = stats?.by_status || {};
  const sum = (statuses: string[]) =>
    statuses.reduce((acc, s) => acc + (byStatus[s] || 0), 0);

  return [
    {
      key: 'total',
      label: 'ВСЕГО',
      icon: Inbox,
      bg: 'bg-slate-100',
      statuses: ['NEW', 'DOCUMENTS_LOADING', 'DOCUMENTS_LOADED', 'PROCESSING', 'SEMANTIC_FILTERING', 'RELEVANT', 'UNCERTAIN', 'SCORING', 'SCORED', 'AWAITING_SUPPLIER_SEARCH', 'SUPPLIER_SEARCH_IN_PROGRESS', 'SUPPLIERS_FOUND', 'NO_SUPPLIERS_FOUND', 'AWAITING_CP', 'CP_REQUESTED', 'CP_PARTIALLY_RECEIVED', 'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION', 'APPROVED', 'REJECTED', 'ERROR'],
      count: stats?.total || 0,
    },
    {
      key: 'relevant',
      label: 'РЕЛЕВАНТНЫЕ',
      icon: FileText,
      bg: 'bg-blue-100',
      statuses: ['RELEVANT', 'UNCERTAIN', 'SCORING', 'SCORED', 'AWAITING_SUPPLIER_SEARCH', 'SUPPLIER_SEARCH_IN_PROGRESS', 'SUPPLIERS_FOUND', 'NO_SUPPLIERS_FOUND', 'AWAITING_CP', 'CP_REQUESTED', 'CP_PARTIALLY_RECEIVED', 'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION', 'APPROVED', 'REJECTED'],
      count: sum(['RELEVANT', 'UNCERTAIN', 'SCORING', 'SCORED', 'AWAITING_SUPPLIER_SEARCH', 'SUPPLIER_SEARCH_IN_PROGRESS', 'SUPPLIERS_FOUND', 'NO_SUPPLIERS_FOUND', 'AWAITING_CP', 'CP_REQUESTED', 'CP_PARTIALLY_RECEIVED', 'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION', 'APPROVED', 'REJECTED']),
    },
    {
      key: 'suppliers',
      label: 'ПОСТАВЩИКИ',
      icon: Users,
      bg: 'bg-blue-100',
      statuses: ['SUPPLIERS_FOUND', 'AWAITING_CP', 'CP_REQUESTED', 'CP_PARTIALLY_RECEIVED', 'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION', 'APPROVED', 'REJECTED'],
      count: sum(['SUPPLIERS_FOUND', 'AWAITING_CP', 'CP_REQUESTED', 'CP_PARTIALLY_RECEIVED', 'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION', 'APPROVED', 'REJECTED']),
    },
    {
      key: 'cp',
      label: 'КП',
      icon: Send,
      bg: 'bg-blue-100',
      statuses: ['CP_PARTIALLY_RECEIVED', 'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION', 'APPROVED', 'REJECTED'],
      count: sum(['CP_PARTIALLY_RECEIVED', 'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION', 'APPROVED', 'REJECTED']),
    },
    {
      key: 'decisions',
      label: 'РЕШЕНИЯ',
      icon: ClipboardCheck,
      bg: 'bg-green-100',
      statuses: ['READY_FOR_DECISION', 'APPROVED', 'REJECTED'],
      count: sum(['READY_FOR_DECISION', 'APPROVED', 'REJECTED']),
    },
  ];
}

function PipelineStageCard({ stage, onNavigate }: { stage: PipelineStage; onNavigate: () => void }) {
  const Icon = stage.icon;
  return (
    <button
      onClick={onNavigate}
      className={cn(
        'flex flex-col items-center justify-center rounded-lg p-4 min-w-[100px] transition-colors cursor-pointer hover:opacity-80',
        stage.bg
      )}
    >
      <Icon className="w-5 h-5 text-slate-500 mb-2" aria-hidden="true" />
      <span className="text-2xl font-semibold text-slate-900">{stage.count}</span>
      <span className="text-xs font-medium text-slate-500 mt-1">{stage.label}</span>
    </button>
  );
}

function ActiveTaskItem({ task }: { task: TaskStatus }) {
  const taskTypeLabels: Record<string, string> = {
    SYNC_TENDERS: 'Синхронизация тендеров',
    PROCESS_TENDER: 'Обработка тендера',
    SEARCH_SUPPLIERS: 'Поиск поставщиков',
    SEND_COMMUNICATIONS: 'Отправка сообщений',
    PARSE_CP: 'Парсинг КП',
    NEGOTIATE: 'Переговоры',
  };
  const label = taskTypeLabels[task.task_type] || task.task_type;
  return (
    <div className="py-2">
      <p className="text-sm text-slate-700 mb-1.5">{label}</p>
      <ProgressBar value={task.progress_percent || 0} size="sm" showLabel />
    </div>
  );
}

function ReadyDecisionItem({ decision, onNavigate }: { decision: DecisionListItem; onNavigate: () => void }) {
  return (
    <button
      onClick={onNavigate}
      className="w-full text-left py-2 group"
    >
      <p className="text-sm font-medium text-slate-900 group-hover:text-blue-600 transition-colors truncate">
        {decision.tender_title}
      </p>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-sm text-green-600 font-medium">
          {decision.best_supplier?.margin_percent != null ? decision.best_supplier.margin_percent.toFixed(1) + '%' : '—'}
        </span>
        <RiskBadge level={decision.risk_assessment?.level || 'LOW'} size="sm" />
      </div>
    </button>
  );
}

export function PipelinePage() {
  const navigate = useNavigate();

  const statsQuery = useQuery({
    queryKey: ['tenders', 'stats'],
    queryFn: () => tendersApi.stats(),
    refetchInterval: 60_000,
  });

  const recentTendersQuery = useQuery({
    queryKey: ['tenders', 'recent'],
    queryFn: () => tendersApi.list({ sort_by: 'updated_at', sort_order: 'desc', per_page: 10 }),
    refetchInterval: 60_000,
  });

  const activeTasksQuery = useQuery({
    queryKey: ['tasks', 'active'],
    queryFn: () => tasksApi.list({ status: 'IN_PROGRESS', per_page: 10 }),
    refetchInterval: 5_000,
  });

  const readyDecisionsQuery = useQuery({
    queryKey: ['decisions', 'ready'],
    queryFn: () => decisionsApi.list({ status: 'READY_FOR_DECISION', per_page: 5 }),
    refetchInterval: 60_000,
  });

  const stages = calculateStages(statsQuery.data);
  const recentTenders = recentTendersQuery.data?.data || [];
  const activeTasks = activeTasksQuery.data?.data || [];
  const readyDecisions = readyDecisionsQuery.data || [];

  const handleRefreshAll = () => {
    statsQuery.refetch();
    recentTendersQuery.refetch();
    activeTasksQuery.refetch();
    readyDecisionsQuery.refetch();
  };

  const getStatusesForStage = (stageKey: string): string => {
    const stage = stages.find((s) => s.key === stageKey);
    return stage?.statuses.join(',') || '';
  };

  return (
    <div>
      <PageHeader
        title="Конвейер"
        description="Обзор работы системы"
        actions={
          <button
            onClick={handleRefreshAll}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Обновить
          </button>
        }
      />

      {/* СЕКЦИЯ 1: ЭТАПЫ КОНВЕЙЕРА */}
      <section className="mb-8">
        {statsQuery.isLoading ? (
          <LoadingSkeleton rows={5} cols={1} type="card" />
        ) : statsQuery.isError ? (
          <ErrorAlert message="Не удалось загрузить статистику" onRetry={() => statsQuery.refetch()} />
        ) : (
          <div className="rounded-lg border border-slate-200 p-4 bg-white">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              {stages.map((stage, index) => (
                <div key={stage.key} className="flex items-center gap-2">
                  <PipelineStageCard
                    stage={stage}
                    onNavigate={() => navigate(`/tenders?status=${getStatusesForStage(stage.key)}`)}
                  />
                  {index < stages.length - 1 && (
                    <ArrowRight className="w-4 h-4 text-slate-300 flex-shrink-0" aria-hidden="true" />
                  )}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-4 flex-wrap">
              {stages.slice(0, -1).map((stage, index) => {
                const nextStage = stages[index + 1];
                const conversion = stage.count > 0 ? ((nextStage.count / stage.count) * 100).toFixed(1) : '0.0';
                return (
                  <span key={stage.key} className="text-xs text-slate-400">
                    {stage.label} → {nextStage.label}: <span className="font-medium text-slate-600">{conversion}%</span>
                    {index < stages.length - 2 && <span className="mx-1">|</span>}
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* СЕКЦИЯ 2: АКТИВНЫЕ ЗАДАЧИ + ГОТОВЫ К РЕШЕНИЮ */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Activity className="h-4 w-4 text-slate-500" aria-hidden="true" />
              Активные задачи
            </h2>
            {activeTasks.length > 0 && !activeTasksQuery.isError && (
              <span className="text-xs font-medium text-slate-500 bg-slate-100 rounded-full px-2 py-0.5">
                {activeTasks.length}
              </span>
            )}
          </div>
          {activeTasksQuery.isLoading ? (
            <LoadingSkeleton rows={3} cols={1} type="card" />
          ) : activeTasksQuery.isError ? (
            <ErrorAlert message="Не удалось загрузить активные задачи" onRetry={() => activeTasksQuery.refetch()} />
          ) : activeTasks.length === 0 ? (
            <EmptyState
              icon={Activity}
              title="Нет активных задач"
              description="Все задачи выполнены. Новые задачи появятся автоматически."
            />
          ) : (
            <div className="divide-y divide-slate-100">
              {activeTasks.map((task) => (
                <ActiveTaskItem key={task.id} task={task} />
              ))}
            </div>
          )}
          <button
            onClick={() => navigate('/tasks')}
            className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
          >
            Все задачи →
          </button>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <ClipboardCheck className="h-4 w-4 text-slate-500" aria-hidden="true" />
              Готовы к решению
            </h2>
            {readyDecisions.length > 0 && !readyDecisionsQuery.isError && (
              <span className="text-xs font-medium text-purple-700 bg-purple-100 rounded-full px-2 py-0.5">
                {readyDecisions.length}
              </span>
            )}
          </div>
          {readyDecisionsQuery.isLoading ? (
            <LoadingSkeleton rows={3} cols={1} type="card" />
          ) : readyDecisionsQuery.isError ? (
            <ErrorAlert message="Не удалось загрузить готовые к решению тендеры" onRetry={() => readyDecisionsQuery.refetch()} />
          ) : readyDecisions.length === 0 ? (
            <EmptyState
              icon={ClipboardCheck}
              title="Нет готовых решений"
              description="Система продолжает работу. Готовые к решению тендеры появятся здесь."
            />
          ) : (
            <div className="divide-y divide-slate-100">
              {readyDecisions.map((decision) => (
                <ReadyDecisionItem
                  key={decision.tender_id}
                  decision={decision}
                  onNavigate={() => navigate('/decisions')}
                />
              ))}
            </div>
          )}
          <button
            onClick={() => navigate('/decisions')}
            className="mt-3 text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
          >
            Все решения →
          </button>
        </div>
      </section>

      {/* СЕКЦИЯ 3: ПОСЛЕДНИЕ ТЕНДЕРЫ */}
      <section className="mb-8">
        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="flex items-center justify-between p-4 border-b border-slate-200">
            <h2 className="text-base font-semibold text-slate-900">Последние тендеры</h2>
            <button
              onClick={() => navigate('/tenders')}
              className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors"
            >
              Все тендеры →
            </button>
          </div>
          {recentTendersQuery.isLoading ? (
            <div className="p-4">
              <LoadingSkeleton rows={5} cols={5} type="table" />
            </div>
          ) : recentTendersQuery.isError ? (
            <div className="p-4">
              <ErrorAlert message="Не удалось загрузить последние тендеры" onRetry={() => recentTendersQuery.refetch()} />
            </div>
          ) : recentTenders.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="Тендеры не найдены"
              description="Система ещё не загрузила тендеры. Проверьте настройки источника."
              actionLabel="Настроить источник"
              onAction={() => navigate('/automation/sources')}
            />
          ) : (
            <div className="divide-y divide-slate-100">
              {recentTenders.map((tender) => (
                <button
                  key={tender.id}
                  onClick={() => navigate(`/tenders/${tender.id}`)}
                  className="w-full flex items-center gap-4 px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">{tender.title}</p>
                  </div>
                  <StatusBadge status={tender.status} size="sm" />
                  <ScoreBadge score={tender.score} size="sm" />
                  <span className="text-sm text-slate-600 w-24 text-right flex-shrink-0">
                    {formatMoney(tender.nmck)}
                  </span>
                  <span className="text-xs text-slate-400 w-20 text-right flex-shrink-0">
                    {formatRelativeTime(tender.updated_at)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* СЕКЦИЯ 4: СВОДКА */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Всего тендеров"
          value={statsQuery.data?.total?.toLocaleString('ru-RU') || '—'}
          icon={Inbox}
          iconBg="bg-slate-100"
          iconText="text-slate-600"
        />
        <StatCard
          title="Одобрено"
          value={(statsQuery.data?.by_status?.APPROVED || 0).toLocaleString('ru-RU')}
          icon={CheckCircle2}
          iconBg="bg-green-100"
          iconText="text-green-700"
        />
        <StatCard
          title="Средняя маржа"
          value={statsQuery.data?.avg_margin_percent ? `${statsQuery.data.avg_margin_percent.toFixed(1)}%` : '—'}
          icon={Gauge}
          iconBg="bg-blue-100"
          iconText="text-blue-700"
        />
        <StatCard
          title="Объём одобренных"
          value={formatMoney(statsQuery.data?.total_approved_volume_rub)}
          icon={Building2}
          iconBg="bg-purple-100"
          iconText="text-purple-700"
        />
      </section>
    </div>
  );
}