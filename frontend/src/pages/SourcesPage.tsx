import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  RadioTower,
  Plus,
  RefreshCw,
  Pencil,
  Trash2,
  Plug,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react';
import { tenderSourcesApi, type TenderSource } from '../api/tenderSources';
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
import { Switch } from '../components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

function SourceFormModal({
  open,
  onOpenChange,
  source,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source?: TenderSource;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    name: source?.name || '',
    type: source?.type || 'aggregator_api',
    api_url: source?.api_url || '',
    api_key: '',
    rate_limit_rps: source?.config?.rate_limit_rps || 5,
    timeout_seconds: source?.config?.timeout_seconds || 30,
    retry_count: source?.config?.retry_count || 3,
    page_size: source?.config?.page_size || 100,
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.api_url.trim()) {
      toast.error('Название и URL обязательны');
      return;
    }
    if (!source && !form.api_key.trim()) {
      toast.error('API-ключ обязателен');
      return;
    }
    setIsLoading(true);
    try {
      const data = {
        name: form.name.trim(),
        type: form.type,
        api_url: form.api_url.trim(),
        api_key: form.api_key || (source ? undefined : ''),
        config: {
          rate_limit_rps: form.rate_limit_rps,
          timeout_seconds: form.timeout_seconds,
          retry_count: form.retry_count,
          page_size: form.page_size,
        },
      };
      if (source?.id) {
        await tenderSourcesApi.put(source.id, data);
        toast.success('Источник обновлён');
      } else {
        await tenderSourcesApi.create(data);
        toast.success('Источник создан');
      }
      onSuccess();
      onOpenChange(false);
    } catch {
      toast.error('Не удалось сохранить источник');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{source ? 'Редактировать источник' : 'Новый источник'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Название *</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Основной агрегатор" />
          </div>
          <div>
            <Label>Тип</Label>
            <Select value={form.type} onValueChange={(value) => setForm({ ...form, type: value })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="aggregator_api">Агрегатор (API)</SelectItem>
                <SelectItem value="direct_api">Прямой API</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>URL API *</Label>
            <Input value={form.api_url} onChange={(e) => setForm({ ...form, api_url: e.target.value })} placeholder="https://api.tenders.example.com/v2" />
          </div>
          <div>
            <Label>API-ключ {source ? '(оставьте пустым, чтобы не менять)' : '*'}</Label>
            <Input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="sk-..." />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Rate limit (запросов/сек)</Label>
              <Input type="number" min={1} value={form.rate_limit_rps} onChange={(e) => setForm({ ...form, rate_limit_rps: Number(e.target.value) })} />
            </div>
            <div>
              <Label>Таймаут (сек)</Label>
              <Input type="number" min={1} value={form.timeout_seconds} onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) })} />
            </div>
            <div>
              <Label>Количество ретраев</Label>
              <Input type="number" min={0} value={form.retry_count} onChange={(e) => setForm({ ...form, retry_count: Number(e.target.value) })} />
            </div>
            <div>
              <Label>Размер страницы</Label>
              <Input type="number" min={1} max={500} value={form.page_size} onChange={(e) => setForm({ ...form, page_size: Number(e.target.value) })} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Сохранение...' : source ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SyncModal({
  open,
  onOpenChange,
  source,
  onSync,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  source: TenderSource;
  onSync: (since: string | null, fullResync: boolean) => void;
  isLoading: boolean;
}) {
  const [mode, setMode] = useState<'last' | 'date' | 'full'>('last');
  const [sinceDate, setSinceDate] = useState('');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Синхронизация: {source?.name}</DialogTitle>
          <DialogDescription>Последняя синхронизация: {source?.last_sync_at ? formatDateTime(source.last_sync_at) : 'никогда'}</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="radio" checked={mode === 'last'} onChange={() => setMode('last')} />
            С последней синхронизации
          </label>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="radio" checked={mode === 'date'} onChange={() => setMode('date')} />
            С указанной даты:
          </label>
          {mode === 'date' && <Input type="date" value={sinceDate} onChange={(e) => setSinceDate(e.target.value)} className="ml-6 w-auto" />}
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input type="radio" checked={mode === 'full'} onChange={() => setMode('full')} />
            Полная синхронизация (может занять время)
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button
            onClick={() => {
              if (mode === 'last') onSync(null, false);
              else if (mode === 'date') onSync(sinceDate, false);
              else onSync(null, true);
            }}
            disabled={isLoading || (mode === 'date' && !sinceDate)}
          >
            {isLoading ? <><Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> Синхронизация...</> : '🔄 Запустить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function SourcesPage() {
  const queryClient = useQueryClient();
  const [formModal, setFormModal] = useState<{ open: boolean; source?: TenderSource }>({ open: false });
  const [syncModal, setSyncModal] = useState<{ open: boolean; source?: TenderSource }>({ open: false });
  const [confirmDeactivate, setConfirmDeactivate] = useState<TenderSource | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  const sourcesQuery = useQuery({
    queryKey: ['tender-sources', 'all'],
    queryFn: () => tenderSourcesApi.list(),
  });

  const syncMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => tenderSourcesApi.sync(id, data),
    onSuccess: (data) => {
      toast.success(`Синхронизация запущена (задача: ${data.task_id?.slice(0, 8)}...)`);
      setSyncModal({ open: false });
    },
    onError: () => toast.error('Не удалось запустить синхронизацию'),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => tenderSourcesApi.testConnection(id),
    onSuccess: (data) => {
      if (data.reachable) {
        toast.success(`Подключение успешно (${data.latency_ms}мс, доступно тендеров: ${data.tenders_available ?? '?'})`);
      } else {
        toast.error(data.error || 'Источник недоступен');
      }
      setTestingId(null);
    },
    onError: () => {
      toast.error('Источник недоступен');
      setTestingId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tenderSourcesApi.delete(id),
    onSuccess: () => {
      toast.success('Источник деактивирован');
      setConfirmDeactivate(null);
      queryClient.invalidateQueries({ queryKey: ['tender-sources'] });
    },
    onError: () => toast.error('Не удалось деактивировать'),
  });

  const sources = sourcesQuery.data || [];

  return (
    <div>
      <PageHeader
        title="Источники тендеров"
        description="API-агрегаторы для получения тендеров"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => sourcesQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Обновить
            </Button>
            <Button size="sm" onClick={() => setFormModal({ open: true })}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Добавить источник
            </Button>
          </>
        }
      />
      {sourcesQuery.isLoading ? (
        <LoadingSkeleton rows={3} cols={1} type="card" />
      ) : sourcesQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить источники" onRetry={() => sourcesQuery.refetch()} />
      ) : sources.length === 0 ? (
        <EmptyState icon={RadioTower} title="Источников нет" description="Подключите API-агрегатор для получения тендеров" actionLabel="Добавить источник" onAction={() => setFormModal({ open: true })} />
      ) : (
        <div className="space-y-4">
          {sources.map((source) => (
            <div key={source.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                    <RadioTower className="h-5 w-5 text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-base font-semibold text-slate-900">{source.name}</p>
                      <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', source.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500')}>
                        {source.is_active ? 'Активен' : 'Неактивен'}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500 mt-0.5">{source.type}</p>
                    <p className="text-xs text-slate-400 mt-0.5 font-mono truncate">{source.api_url}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-slate-500 flex-wrap">
                      <span>Последняя синхронизация: {source.last_sync_at ? formatRelativeTime(source.last_sync_at) : 'никогда'}</span>
                      {source.last_sync_status === 'success' && <span className="inline-flex items-center gap-1 text-green-600"><CheckCircle2 className="h-3 w-3" /> Успешно</span>}
                      {source.last_sync_status === 'error' && <span className="inline-flex items-center gap-1 text-red-600"><XCircle className="h-3 w-3" /> Ошибка</span>}
                      <span>Всего: {source.tenders_synced_total || 0}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Switch
                    checked={source.is_active}
                    onCheckedChange={async (checked) => {
                      try {
                        await tenderSourcesApi.patch(source.id, { is_active: checked });
                        toast.success(checked ? 'Источник активирован' : 'Источник деактивирован');
                        queryClient.invalidateQueries({ queryKey: ['tender-sources'] });
                      } catch {
                        toast.error('Не удалось изменить статус');
                      }
                    }}
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <Button variant="outline" size="sm" onClick={() => setSyncModal({ open: true, source })}>
                  <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                  Синхронизировать
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setTestingId(source.id);
                    testMutation.mutate(source.id);
                  }}
                  disabled={testingId === source.id}
                >
                  {testingId === source.id ? <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" /> : <Plug className="h-3.5 w-3.5 mr-1.5" />}
                  Проверить
                </Button>
                <Button variant="outline" size="sm" onClick={() => setFormModal({ open: true, source })}>
                  <Pencil className="h-3.5 w-3.5 mr-1.5" />
                  Редактировать
                </Button>
                <Button variant="outline" size="sm" onClick={() => setConfirmDeactivate(source)}>
                  <Trash2 className="h-3.5 w-3.5 mr-1.5 text-red-500" />
                  Деактивировать
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <SourceFormModal
        open={formModal.open}
        onOpenChange={(open) => setFormModal({ open, source: formModal.source })}
        source={formModal.source}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ['tender-sources'] })}
      />
      <SyncModal
        open={syncModal.open}
        onOpenChange={(open) => setSyncModal((prev) => ({ ...prev, open }))}
        source={syncModal.source as TenderSource}
        onSync={(since, fullResync) => {
          if (syncModal.source) {
            syncMutation.mutate({ id: syncModal.source.id, data: { since, full_resync: fullResync } });
          }
        }}
        isLoading={syncMutation.isPending}
      />
      <ConfirmDialog
        open={!!confirmDeactivate}
        onOpenChange={(open) => !open && setConfirmDeactivate(null)}
        title="Деактивировать источник"
        description={confirmDeactivate ? `Источник «${confirmDeactivate.name}» будет деактивирован.` : ''}
        confirmLabel="Деактивировать"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={() => confirmDeactivate && deleteMutation.mutate(confirmDeactivate.id)}
      />
    </div>
  );
}