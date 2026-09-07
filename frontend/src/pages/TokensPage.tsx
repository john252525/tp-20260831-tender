import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  KeyRound,
  Plus,
  RefreshCw,
  Trash2,
  Copy,
  Check,
  Ban,
} from 'lucide-react';
import { tokensApi, type ApiTokenListItem, type ApiTokenCreated } from '../api/tokens';
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';

function CreateTokenModal({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (token: ApiTokenCreated) => void;
}) {
  const [form, setForm] = useState({
    description: '',
    rate_limit_per_minute: '60',
    expires_in_days: '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.description.trim()) {
      toast.error('Описание обязательно');
      return;
    }
    setIsLoading(true);
    try {
      const result = await tokensApi.create({
        description: form.description.trim(),
        rate_limit_per_minute: Number(form.rate_limit_per_minute) || undefined,
        expires_in_days: form.expires_in_days ? Number(form.expires_in_days) : null,
      });
      toast.success('Токен создан');
      onSuccess(result);
      onOpenChange(false);
      setForm({ description: '', rate_limit_per_minute: '60', expires_in_days: '' });
    } catch {
      toast.error('Не удалось создать токен');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Новый API-токен</DialogTitle>
          <DialogDescription>Токен будет показан только один раз</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Описание *</Label>
            <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Скрипт обновления" />
          </div>
          <div>
            <Label>Лимит запросов в минуту</Label>
            <Input type="number" min={1} max={1000} value={form.rate_limit_per_minute} onChange={(e) => setForm({ ...form, rate_limit_per_minute: e.target.value })} />
          </div>
          <div>
            <Label>Срок действия (дней, пусто = бессрочный)</Label>
            <Input type="number" min={1} value={form.expires_in_days} onChange={(e) => setForm({ ...form, expires_in_days: e.target.value })} placeholder="бессрочный" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Создание...' : 'Создать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ShowTokenModal({
  token,
  onOpenChange,
}: {
  token: ApiTokenCreated | null;
  onOpenChange: (open: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    if (!token) return;
    await navigator.clipboard.writeText(token.token);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  if (!token) return null;

  return (
    <Dialog open={!!token} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Токен создан</DialogTitle>
          <DialogDescription>Скопируйте токен сейчас. Он больше не будет показан.</DialogDescription>
        </DialogHeader>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-center justify-between gap-2">
            <code className="text-sm font-mono text-slate-900 break-all">{token.token}</code>
            <button onClick={handleCopy} className={cn('p-2 rounded-md flex-shrink-0 transition-colors', copied ? 'bg-green-100 text-green-600' : 'bg-slate-100 text-slate-500 hover:bg-slate-200')} aria-label="Копировать">
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Готово</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function TokensPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newToken, setNewToken] = useState<ApiTokenCreated | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    type: 'deactivate' | 'delete';
    token: ApiTokenListItem;
  } | null>(null);

  const tokensQuery = useQuery({
    queryKey: ['tokens', 'all'],
    queryFn: () => tokensApi.list(),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => tokensApi.patch(id, { is_active: false }),
    onSuccess: () => {
      toast.success('Токен деактивирован');
      setConfirmAction(null);
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
    onError: () => toast.error('Не удалось деактивировать'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tokensApi.delete(id),
    onSuccess: () => {
      toast.success('Токен удалён');
      setConfirmAction(null);
      queryClient.invalidateQueries({ queryKey: ['tokens'] });
    },
    onError: () => toast.error('Не удалось удалить'),
  });

  const tokens = tokensQuery.data || [];

  return (
    <div>
      <PageHeader
        title="API-токены"
        description="Токены для программного доступа к API"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => tokensQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Обновить
            </Button>
            <Button size="sm" onClick={() => setShowCreate(true)}>
              <Plus className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Создать токен
            </Button>
          </>
        }
      />
      {tokensQuery.isLoading ? (
        <LoadingSkeleton rows={5} cols={6} type="table" />
      ) : tokensQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить токены" onRetry={() => tokensQuery.refetch()} />
      ) : tokens.length === 0 ? (
        <EmptyState icon={KeyRound} title="Токенов нет" description="Создайте токен для доступа к API" actionLabel="Создать токен" onAction={() => setShowCreate(true)} />
      ) : (
        <div className="rounded-lg border border-slate-200 overflow-hidden bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Описание</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Токен</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Активен</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Rate limit</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Последнее использование</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Истекает</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Создан</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Действия</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((token) => (
                <tr key={token.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 text-slate-900 font-medium">{token.description}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">{token.token_preview}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', token.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500')}>
                      {token.is_active ? 'Да' : 'Нет'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-600">{token.rate_limit_per_minute || 60}</td>
                  <td className="px-4 py-3 text-xs text-slate-600">{token.last_used_at ? formatRelativeTime(token.last_used_at) : 'никогда'}</td>
                  <td className="px-4 py-3 text-xs text-slate-600">{token.expires_at ? formatDateTime(token.expires_at) : '—'}</td>
                  <td className="px-4 py-3 text-xs text-slate-600">{formatDateTime(token.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {token.is_active && (
                        <button onClick={() => setConfirmAction({ type: 'deactivate', token })} className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-yellow-600 transition-colors" aria-label="Деактивировать">
                          <Ban className="h-4 w-4" aria-hidden="true" />
                        </button>
                      )}
                      <button onClick={() => setConfirmAction({ type: 'delete', token })} className="p-1.5 rounded-md text-slate-400 hover:bg-slate-100 hover:text-red-600 transition-colors" aria-label="Удалить">
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <CreateTokenModal
        open={showCreate}
        onOpenChange={setShowCreate}
        onSuccess={(token) => {
          setNewToken(token);
          queryClient.invalidateQueries({ queryKey: ['tokens'] });
        }}
      />
      <ShowTokenModal token={newToken} onOpenChange={(open) => !open && setNewToken(null)} />

      <ConfirmDialog
        open={!!confirmAction}
        onOpenChange={(open) => !open && setConfirmAction(null)}
        title={confirmAction?.type === 'deactivate' ? 'Деактивировать токен' : 'Удалить токен'}
        description={confirmAction ? `Токен «${confirmAction.token.description}» будет ${confirmAction.type === 'deactivate' ? 'деактивирован' : 'удалён навсегда'}.` : ''}
        confirmLabel={confirmAction?.type === 'deactivate' ? 'Деактивировать' : 'Удалить'}
        variant={confirmAction?.type === 'delete' ? 'destructive' : 'default'}
        isLoading={deactivateMutation.isPending || deleteMutation.isPending}
        onConfirm={() => {
          if (!confirmAction) return;
          if (confirmAction.type === 'deactivate') deactivateMutation.mutate(confirmAction.token.id);
          else deleteMutation.mutate(confirmAction.token.id);
        }}
      />
    </div>
  );
}