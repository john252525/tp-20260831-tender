import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Webhook,
  Plus,
  RefreshCw,
  Pencil,
  Trash2,
  Send,
  CheckCircle2,
  XCircle,
  Loader2,
} from 'lucide-react';
import { webhooksApi, type Webhook as WebhookType } from '../api/webhooks';
import { TagChip } from '../components/common/TagChip';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { PageHeader } from '../components/common/PageHeader';
import { formatRelativeTime } from '../lib/formatters';
import { cn } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';
import { Switch } from '../components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';

const WEBHOOK_EVENTS = [
  { value: 'tender.ready_for_decision', label: 'Тендер готов к решению' },
  { value: 'cp.received', label: 'Получено КП' },
  { value: 'task.completed', label: 'Задача завершена' },
  { value: 'task.failed', label: 'Задача провалена' },
];

function WebhookFormModal({
  open,
  onOpenChange,
  webhook,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  webhook?: WebhookType;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    url: webhook?.url || '',
    events: webhook?.events || [],
    secret: webhook?.secret || '',
    is_active: webhook?.is_active ?? true,
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.url.trim()) {
      toast.error('URL обязателен');
      return;
    }
    if (form.events.length === 0) {
      toast.error('Выберите хотя бы одно событие');
      return;
    }
    if (!form.url.startsWith('https://') && !form.url.startsWith('http://')) {
      toast.error('URL должен начинаться с http:// или https://');
      return;
    }
    setIsLoading(true);
    try {
      const data = {
        url: form.url.trim(),
        events: form.events,
        secret: form.secret.trim(),
        is_active: form.is_active,
      };
      if (webhook?.id) {
        await webhooksApi.patch(webhook.id, data);
        toast.success('Вебхук обновлён');
      } else {
        await webhooksApi.create(data);
        toast.success('Вебхук создан');
      }
      onSuccess();
      onOpenChange(false);
    } catch {
      toast.error('Не удалось сохранить');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleEvent = (value: string) => {
    setForm((prev) => ({
      ...prev,
      events: prev.events.includes(value)
        ? prev.events.filter((e) => e !== value)
        : [...prev.events, value],
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{webhook ? 'Редактировать вебхук' : 'Новый вебхук'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>URL *</Label>
            <Input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://my-system.com/hooks/tender-bot" />
          </div>
          <div>
            <Label>События *</Label>
            <div className="space-y-2 mt-2">
              {WEBHOOK_EVENTS.map((event) => (
                <label key={event.value} className="flex items-center gap-2 text-sm cursor-pointer">
                  <Checkbox checked={form.events.includes(event.value)} onCheckedChange={() => toggleEvent(event.value)} />
                  {event.label}
                  <span className="text-xs text-slate-400">({event.value})</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <Label>Secret (для HMAC-подписи, опционально)</Label>
            <Input type="password" value={form.secret} onChange={(e) => setForm({ ...form, secret: e.target.value })} placeholder="my-secret-key" />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <Checkbox checked={form.is_active} onCheckedChange={(checked) => setForm({ ...form, is_active: !!checked })} />
            Активен
          </label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Сохранение...' : webhook ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function WebhooksPage() {
  const queryClient = useQueryClient();
  const [formModal, setFormModal] = useState<{ open: boolean; webhook?: WebhookType }>({ open: false });
  const [confirmDelete, setConfirmDelete] = useState<WebhookType | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  const webhooksQuery = useQuery({
    queryKey: ['webhooks', 'all'],
    queryFn: () => webhooksApi.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => webhooksApi.delete(id),
    onSuccess: () => {
      toast.success('Вебхук удалён');
      setConfirmDelete(null);
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
    onError: () => toast.error('Не удалось удалить'),
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => webhooksApi.test(id),
    onSuccess: (data) => {
      if (data.delivered) {
        toast.success(`Тестовый вызов доставлен (HTTP ${data.response_status})`);
      } else {
        toast.error(data.error || 'Не удалось доставить');
      }
      setTestingId(null);
    },
    onError: () => {
      toast.error('Не удалось доставить');
      setTestingId(null);
    },
  });

  const webhooks = webhooksQuery.data || [];

  return (
    <div>
      <PageHeader
        title="Вебхуки"
        description="Интеграции с внешними системами"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => webhooksQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Обновить
            </Button>
            <Button size="sm" onClick={() => setFormModal({ open: true })}>
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Добавить
            </Button>
          </>
        }
      />

      {webhooksQuery.isLoading ? (
        <LoadingSkeleton rows={3} cols={1} type="card" />
      ) : webhooksQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить вебхуки" onRetry={() => webhooksQuery.refetch()} />
      ) : webhooks.length === 0 ? (
        <EmptyState icon={Webhook} title="Вебхуков нет" description="Создайте вебхук для интеграции с внешними системами" actionLabel="Добавить вебхук" onAction={() => setFormModal({ open: true })} />
      ) : (
        <div className="space-y-3">
          {webhooks.map((webhook) => (
            <div key={webhook.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Webhook className="h-4 w-4 text-slate-400" aria-hidden="true" />
                    <p className="text-sm font-semibold text-slate-900 font-mono truncate">{webhook.url}</p>
                  </div>
                  <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                    {(webhook.events || []).map((event) => <TagChip key={event} label={event} />)}
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
                    <span>Последний вызов: {webhook.last_sent_at ? formatRelativeTime(webhook.last_sent_at) : 'никогда'}</span>
                    {webhook.last_status === 'success' && <span className="inline-flex items-center gap-1 text-green-600"><CheckCircle2 className="h-3 w-3" /> Доставлено</span>}
                    {webhook.last_status === 'error' && <span className="inline-flex items-center gap-1 text-red-600"><XCircle className="h-3 w-3" /> Ошибка</span>}
                    <span>Ретраев: {webhook.retry_count || 0}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Switch
                    checked={webhook.is_active}
                    onCheckedChange={async (checked) => {
                      try {
                        await webhooksApi.patch(webhook.id, { is_active: checked });
                        toast.success(checked ? 'Вебхук активирован' : 'Вебхук деактивирован');
                        queryClient.invalidateQueries({ queryKey: ['webhooks'] });
                      } catch {
                        toast.error('Не удалось изменить');
                      }
                    }}
                  />
                  <Button variant="outline" size="sm" onClick={() => { setTestingId(webhook.id); testMutation.mutate(webhook.id); }} disabled={testingId === webhook.id}>
                    {testingId === webhook.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setFormModal({ open: true, webhook })}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setConfirmDelete(webhook)}>
                    <Trash2 className="h-3.5 w-3.5 text-red-500" />
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <WebhookFormModal
        open={formModal.open}
        onOpenChange={(open) => setFormModal({ open, webhook: formModal.webhook })}
        webhook={formModal.webhook}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ['webhooks'] })}
      />

      <ConfirmDialog
        open={!!confirmDelete}
        onOpenChange={(open) => !open && setConfirmDelete(null)}
        title="Удалить вебхук"
        description={confirmDelete ? `Вебхук «${confirmDelete.url}» будет удалён.` : ''}
        confirmLabel="Удалить"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={() => confirmDelete && deleteMutation.mutate(confirmDelete.id)}
      />
    </div>
  );
}