import { useState, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Activity,
  RefreshCw,
  Ban,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  FileText,
  Building2,
  Send,
  Calculator,
  MessagesSquare,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { tasksApi, type TaskStatus } from '../api/tasks';
import { ProgressBar } from '../components/common/ProgressBar';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../components/ui/tooltip';

const TASK_TYPE_CONFIG: Record<string, { label: string; icon: LucideIcon; bg: string; text: string }> = {
  SYNC_TENDERS: { label: 'Синхронизация', icon: RefreshCw, bg: 'bg-slate-100', text: 'text-slate-700' },
  PROCESS_TENDER: { label: 'Обработка тендера', icon: Calculator, bg: 'bg-blue-100', text: 'text-blue-700' },
  SEARCH_SUPPLIERS: { label: 'Поиск поставщиков', icon: Users, bg: 'bg-purple-100', text: 'text-purple-700' },
  SEND_COMMUNICATIONS: { label: 'Отправка сообщений', icon: Send, bg: 'bg-green-100', text: 'text-green-700' },
  PARSE_CP: { label: 'Парсинг КП', icon: FileText, bg: 'bg-yellow-100', text: 'text-yellow-700' },
  NEGOTIATE: { label: 'Переговоры', icon: MessagesSquare, bg: 'bg-orange-100', text: 'text-orange-700' },
};

const TASK_STATUS_CONFIG: Record<string, { label: string; bg: string; text: string; icon: LucideIcon }> = {
  PENDING: { label: 'Ожидает', bg: 'bg-slate-100', text: 'text-slate-700', icon: Clock },
  IN_PROGRESS: { label: 'Выполняется', bg: 'bg-blue-100', text: 'text-blue-700', icon: Loader2 },
  COMPLETED: { label: 'Завершена', bg: 'bg-green-100', text: 'text-green-700', icon: CheckCircle2 },
  FAILED: { label: 'Ошибка', bg: 'bg-red-100', text: 'text-red-700', icon: XCircle },
  CANCELLED: { label: 'Отменена', bg: 'bg-slate-100', text: 'text-slate-500', icon: Ban },
};

export function TasksPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [showFilters, setShowFilters] = useState(false);
  const [cancelTask, setCancelTask] = useState<TaskStatus | null>(null);

  const filters = useMemo(() => ({
    status: searchParams.get('status') || '',
    task_type: searchParams.get('task_type') || '',
    entity_type: searchParams.get('entity_type') || '',
    entity_id: searchParams.get('entity_id') || '',
    page: Number(searchParams.get('page') || 1),
    per_page: Number(searchParams.get('per_page') || 20),
  }), [searchParams]);

  const tasksQuery = useQuery({
    queryKey: ['tasks', 'list', filters],
    queryFn: () =>
      tasksApi.list({
        status: filters.status || undefined,
        task_type: filters.task_type || undefined,
        entity_type: filters.entity_type || undefined,
        entity_id: filters.entity_id || undefined,
        page: filters.page,
        per_page: filters.per_page,
      }),
    refetchInterval: (query) => {
      const data = query.state.data?.data;
      const hasActive = data?.some((task) => ['PENDING', 'IN_PROGRESS'].includes(task.status));
      return hasActive ? 3000 : 15000;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.cancel(taskId),
    onSuccess: () => {
      toast.success('Задача отменена');
      setCancelTask(null);
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: () => toast.error('Не удалось отменить задачу'),
  });

  const updateFilters = (updates: Record<string, string | null>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === '') {
        newParams.delete(key);
      } else {
        newParams.set(key, value);
      }
    });
    setSearchParams(newParams, { replace: true });
  };

  const resetFilters = () => {
    setSearchParams({}, { replace: true });
  };

  const tasks = tasksQuery.data?.data || [];
  const meta = tasksQuery.data?.meta;

  const getEntityLink = (task: TaskStatus): string | null => {
    if (!task.entity_type || !task.entity_id) return null;
    switch (task.entity_type) {
      case 'tender': return `/tenders/${task.entity_id}`;
      case 'supplier': return `/suppliers/${task.entity_id}`;
      default: return null;
    }
  };

  return (
    <div>
      <PageHeader
        title="Задачи"
        description="Асинхронные операции системы"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
              <Search className="h-3.5 w-3.5 mr-1.5" />
              Фильтры
            </Button>
            <Button variant="outline" size="sm" onClick={() => tasksQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Обновить
            </Button>
          </>
        }
      />

      {showFilters && (
        <div className="rounded-lg border border-slate-200 p-4 mb-6 bg-white">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <Label className="text-xs text-slate-500">Статус</Label>
              <Select value={filters.status || 'all'} onValueChange={(value) => updateFilters({ status: value === 'all' ? '' : value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все</SelectItem>
                  <SelectItem value="PENDING">Ожидает</SelectItem>
                  <SelectItem value="IN_PROGRESS">Выполняется</SelectItem>
                  <SelectItem value="COMPLETED">Завершена</SelectItem>
                  <SelectItem value="FAILED">Ошибка</SelectItem>
                  <SelectItem value="CANCELLED">Отменена</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Тип задачи</Label>
              <Select value={filters.task_type || 'all'} onValueChange={(value) => updateFilters({ task_type: value === 'all' ? '' : value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все</SelectItem>
                  <SelectItem value="SYNC_TENDERS">Синхронизация</SelectItem>
                  <SelectItem value="PROCESS_TENDER">Обработка тендера</SelectItem>
                  <SelectItem value="SEARCH_SUPPLIERS">Поиск поставщиков</SelectItem>
                  <SelectItem value="SEND_COMMUNICATIONS">Отправка сообщений</SelectItem>
                  <SelectItem value="PARSE_CP">Парсинг КП</SelectItem>
                  <SelectItem value="NEGOTIATE">Переговоры</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Тип сущности</Label>
              <Select value={filters.entity_type || 'all'} onValueChange={(value) => updateFilters({ entity_type: value === 'all' ? '' : value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все</SelectItem>
                  <SelectItem value="tender">Тендер</SelectItem>
                  <SelectItem value="supplier">Поставщик</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">ID сущности</Label>
              <Input
                placeholder="uuid"
                defaultValue={filters.entity_id}
                onChange={(e) => updateFilters({ entity_id: e.target.value })}
                className="mt-1 font-mono text-xs"
              />
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button variant="outline" size="sm" onClick={resetFilters}>
              Сбросить
            </Button>
          </div>
        </div>
      )}

      {tasksQuery.isLoading ? (
        <LoadingSkeleton rows={8} cols={6} type="table" />
      ) : tasksQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить задачи" onRetry={() => tasksQuery.refetch()} />
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="Задач нет"
          description="Новые задачи появятся при запуске операций"
        />
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Тип</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Статус</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase w-[200px]">Прогресс</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Сущность</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Создана</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Завершена</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Ошибка</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Действия</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const typeConfig = TASK_TYPE_CONFIG[task.task_type] || { label: task.task_type, icon: FileText, bg: 'bg-slate-100', text: 'text-slate-700' };
                const statusConfig = TASK_STATUS_CONFIG[task.status] || { label: task.status, bg: 'bg-slate-100', text: 'text-slate-700', icon: Clock };
                const TypeIcon = typeConfig.icon;
                const StatusIcon = statusConfig.icon;
                const entityLink = getEntityLink(task);
                return (
                  <tr key={task.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium', typeConfig.bg, typeConfig.text)}>
                        <TypeIcon className="h-3 w-3" />
                        {typeConfig.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium', statusConfig.bg, statusConfig.text)}>
                        <StatusIcon className={cn('h-3 w-3', task.status === 'IN_PROGRESS' && 'animate-spin')} />
                        {statusConfig.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <ProgressBar
                        value={task.progress_percent || 0}
                        size="sm"
                        showLabel
                        animate={task.status === 'IN_PROGRESS'}
                      />
                    </td>
                    <td className="px-4 py-3">
                      {entityLink ? (
                        <button
                          onClick={() => navigate(entityLink)}
                          className="text-sm text-blue-600 hover:underline"
                        >
                          {task.entity_type}: {task.entity_id?.slice(0, 8)}...
                        </button>
                      ) : (
                        <span className="text-sm text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600" title={formatDateTime(task.created_at)}>
                      {formatRelativeTime(task.created_at)}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {task.completed_at ? formatRelativeTime(task.completed_at) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {task.error_message ? (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger>
                              <span className="inline-flex items-center gap-1 text-xs text-red-600">
                                <AlertCircle className="h-3.5 w-3.5" />
                                {task.error_message.slice(0, 30)}...
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <p className="text-xs">{task.error_message}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {['PENDING', 'IN_PROGRESS'].includes(task.status) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setCancelTask(task)}
                        >
                          <Ban className="h-3.5 w-3.5 mr-1 text-red-500" />
                          Отменить
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {meta && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50">
              <span className="text-sm text-slate-500">
                Показано {tasks.length} из {meta.total}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={filters.page <= 1}
                  onClick={() => updateFilters({ page: String(filters.page - 1) })}
                >
                  ←
                </Button>
                <span className="text-sm text-slate-600">{filters.page} / {meta.pages}</span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={filters.page >= meta.pages}
                  onClick={() => updateFilters({ page: String(filters.page + 1) })}
                >
                  →
                </Button>
                <Select
                  value={String(filters.per_page)}
                  onValueChange={(value) => updateFilters({ per_page: value, page: '1' })}
                >
                  <SelectTrigger className="w-[90px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={!!cancelTask}
        onOpenChange={(open) => !open && setCancelTask(null)}
        title="Отменить задачу"
        description={
          cancelTask
            ? `Задача «${TASK_TYPE_CONFIG[cancelTask.task_type]?.label || cancelTask.task_type}» будет отменена.`
            : ''
        }
        confirmLabel="Отменить"
        variant="destructive"
        isLoading={cancelMutation.isPending}
        onConfirm={() => cancelTask && cancelMutation.mutate(cancelTask.id)}
      />
    </div>
  );
}