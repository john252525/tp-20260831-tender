import { useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ClipboardCheck,
  Check,
  X,
  RefreshCw,
  Search,
  Banknote,
  Calendar,
  AlertTriangle,
  UserX,
  HelpCircle,
  type LucideIcon,
} from 'lucide-react';
import { decisionsApi, type DecisionListItem } from '../api/decisions';
import { RiskBadge } from '../components/common/RiskBadge';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
import { formatMoney, formatDate } from '../lib/formatters';
import { cn } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
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

function getRiskIcon(type: string): LucideIcon {
  switch (type) {
    case 'price': return Banknote;
    case 'deadline': return Calendar;
    case 'compliance': return AlertTriangle;
    case 'supplier': return UserX;
    default: return HelpCircle;
  }
}

function getRiskLevelColor(level: string) {
  switch (level) {
    case 'LOW': return 'text-green-700';
    case 'MEDIUM': return 'text-yellow-700';
    case 'HIGH': return 'text-red-700';
    default: return 'text-slate-500';
  }
}

function ApproveModal({
  open,
  onOpenChange,
  decision,
  onConfirm,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  decision: DecisionListItem;
  onConfirm: (supplierId: string, offerId: string, comment: string) => void;
  isLoading: boolean;
}) {
  const [chosenSupplierId, setChosenSupplierId] = useState('');
  const [chosenOfferId, setChosenOfferId] = useState('');
  const [comment, setComment] = useState('');
  const bestSupplier = decision?.best_supplier;
  const alternatives = decision?.alternative_suppliers || [];

  const handleOpen = () => {
    if (bestSupplier) {
      setChosenSupplierId(bestSupplier.id);
      setChosenOfferId(bestSupplier.offer_id);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(open) => {
      if (open) handleOpen();
      onOpenChange(open);
    }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Одобрить тендер</DialogTitle>
          <DialogDescription>Подтвердите выбор поставщика для исполнения контракта</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Поставщик</Label>
            <Select
              value={chosenSupplierId}
              onValueChange={(value) => {
                setChosenSupplierId(value);
                if (value === bestSupplier?.id) setChosenOfferId(bestSupplier.offer_id);
                else {
                  const alt = alternatives.find((a: any) => a.id === value);
                  setChosenOfferId(alt?.offer_id || '');
                }
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Выберите поставщика" />
              </SelectTrigger>
              <SelectContent>
                {bestSupplier && (
                  <SelectItem value={bestSupplier.id}>
                    {bestSupplier.name} — {bestSupplier.margin_percent.toFixed(1)}%
                  </SelectItem>
                )}
                {alternatives.map((alt: any) => (
                  <SelectItem key={alt.id} value={alt.id}>
                    {alt.name} — {alt.margin_percent.toFixed(1)}%
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Комментарий (опционально)</Label>
            <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Например: отличная маржа, подтверждаю" rows={3} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={() => onConfirm(chosenSupplierId, chosenOfferId, comment)} disabled={!chosenSupplierId || isLoading}>
            {isLoading ? 'Подтверждение...' : '✅ Подтвердить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RejectModal({
  open,
  onOpenChange,
  onConfirm,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (reason: string, comment: string) => void;
  isLoading: boolean;
}) {
  const [reason, setReason] = useState('low_margin');
  const [comment, setComment] = useState('');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Отклонить тендер</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Причина</Label>
            <div className="space-y-2 mt-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" checked={reason === 'low_margin'} onChange={() => setReason('low_margin')} />
                Низкая маржа
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" checked={reason === 'high_risk'} onChange={() => setReason('high_risk')} />
                Высокий риск
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" checked={reason === 'not_interested'} onChange={() => setReason('not_interested')} />
                Не интересно
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" checked={reason === 'other'} onChange={() => setReason('other')} />
                Другое
              </label>
            </div>
          </div>
          <div>
            <Label>Комментарий (опционально)</Label>
            <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Опишите причину..." rows={3} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button variant="destructive" onClick={() => onConfirm(reason, comment)} disabled={isLoading}>
            {isLoading ? 'Отклонение...' : '❌ Отклонить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RequestInfoModal({
  open,
  onOpenChange,
  onConfirm,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (instructions: string, returnToStage: string) => void;
  isLoading: boolean;
}) {
  const [instructions, setInstructions] = useState('');
  const [returnToStage, setReturnToStage] = useState('negotiation');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Запросить дополнительную информацию</DialogTitle>
          <DialogDescription>Система вернёт тендер на доработку</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Инструкция (что уточнить)</Label>
            <Textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} placeholder="Уточните, включает ли цена доставку до склада заказчика" rows={4} />
          </div>
          <div>
            <Label>Вернуться на этап</Label>
            <Select value={returnToStage} onValueChange={setReturnToStage}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="negotiation">Переговоры</SelectItem>
                <SelectItem value="cp_request">Запрос КП</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={() => onConfirm(instructions, returnToStage)} disabled={!instructions.trim() || isLoading}>
            {isLoading ? 'Отправка...' : 'Отправить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DecisionCard({
  decision,
  onApprove,
  onReject,
  onRequestInfo,
  isLoading,
}: {
  decision: DecisionListItem;
  onApprove: () => void;
  onReject: () => void;
  onRequestInfo: () => void;
  isLoading: boolean;
}) {
  const bestSupplier = decision.best_supplier;
  const alternatives = decision.alternative_suppliers || [];
  const risk = decision.risk_assessment;
  const daysLeft = decision.deadline_at
    ? Math.ceil((new Date(decision.deadline_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
      <div className="p-4 border-b border-slate-100">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-slate-900 truncate">{decision.tender_title}</h3>
            <div className="flex items-center gap-3 mt-1 flex-wrap text-sm text-slate-600">
              <span>НМЦК: <span className="font-medium">{formatMoney(decision.nmck)}</span></span>
              <span>Дедлайн: <span className="font-medium">{formatDate(decision.deadline_at)}</span></span>
              {daysLeft !== null && (
                <span className={cn(
                  'text-xs font-medium rounded-full px-2 py-0.5',
                  daysLeft < 3 ? 'bg-red-100 text-red-700' : daysLeft < 7 ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                )}>
                  {daysLeft > 0 ? `Осталось: ${daysLeft} дн.` : 'Просрочено'}
                </span>
              )}
            </div>
          </div>
          <RiskBadge level={risk?.level || 'LOW'} />
        </div>
      </div>

      <div className="p-4 border-b border-slate-100 bg-green-50/30">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-green-700 uppercase mb-1">🏆 Лучший поставщик</p>
            <p className="text-sm font-semibold text-slate-900">{bestSupplier?.name || '—'}</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-600">Финальная цена: <span className="font-medium">{formatMoney(bestSupplier?.final_price)}</span></p>
            <p className="text-sm font-semibold text-green-700">
              Маржа: {bestSupplier?.margin_percent != null ? `${bestSupplier.margin_percent.toFixed(1)}%` : '—'} ({formatMoney((decision.nmck || 0) - (bestSupplier?.final_price || 0))})
            </p>
          </div>
        </div>
      </div>

      <div className="p-4 border-b border-slate-100">
        <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Риски</p>
        <div className="space-y-1.5">
          {risk?.factors?.map((factor, index) => {
            const Icon = getRiskIcon(factor.type);
            return (
              <div key={index} className="flex items-center gap-2">
                <Icon className={cn('h-4 w-4 flex-shrink-0', getRiskLevelColor(factor.level))} aria-hidden="true" />
                <span className="text-xs font-medium text-slate-500 uppercase w-24">{factor.type}:</span>
                <span className={cn('text-xs font-semibold', getRiskLevelColor(factor.level))}>{factor.level}</span>
                <span className="text-xs text-slate-500">— {factor.description}</span>
              </div>
            );
          })}
        </div>
      </div>

      {alternatives.length > 0 && (
        <div className="p-4 border-b border-slate-100">
          <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Альтернативы</p>
          {alternatives.map((alt) => (
            <div key={alt.id} className="flex justify-between text-sm py-0.5">
              <span className="text-slate-600">{alt.name}</span>
              <span className="font-medium text-slate-900">{alt.margin_percent.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      )}

      <div className="p-4 flex gap-2">
        <Button onClick={onApprove} disabled={isLoading} className="flex-1">
          <Check className="h-4 w-4 mr-1.5" />
          Одобрить
        </Button>
        <Button variant="outline" onClick={onReject} disabled={isLoading} className="flex-1">
          <X className="h-4 w-4 mr-1.5" />
          Отклонить
        </Button>
        <Button variant="outline" onClick={onRequestInfo} disabled={isLoading} className="flex-1">
          <HelpCircle className="h-4 w-4 mr-1.5" />
          Уточнить
        </Button>
      </div>
    </div>
  );
}

export function DecisionsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [showFilters, setShowFilters] = useState(false);
  const [modalState, setModalState] = useState<{
    type: 'none' | 'approve' | 'reject' | 'info';
    decision?: DecisionListItem;
  }>({ type: 'none' });

  const filters = useMemo(() => ({
    status: searchParams.get('status') || 'READY_FOR_DECISION',
    risk_level: searchParams.get('risk_level') || '',
    min_margin: searchParams.get('min_margin') || '',
    sort_by: searchParams.get('sort_by') || 'margin_percent',
    sort_order: (searchParams.get('sort_order') as 'asc' | 'desc') || 'desc',
    page: Number(searchParams.get('page') || 1),
    per_page: Number(searchParams.get('per_page') || 20),
  }), [searchParams]);

  const decisionsQuery = useQuery({
    queryKey: ['decisions', 'list', filters],
    queryFn: () =>
      decisionsApi.list({
        status: filters.status,
        risk_level: filters.risk_level || undefined,
        min_margin: filters.min_margin ? Number(filters.min_margin) : undefined,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
        page: filters.page,
        per_page: filters.per_page,
      }),
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

  const approveMutation = useMutation({
    mutationFn: ({ tenderId, supplierId, offerId, comment }: { tenderId: string; supplierId: string; offerId: string; comment: string }) =>
      decisionsApi.approve(tenderId, { chosen_supplier_id: supplierId, chosen_offer_id: offerId, comment: comment || undefined }),
    onSuccess: () => {
      toast.success('Тендер одобрен ✅');
      setModalState({ type: 'none' });
      queryClient.invalidateQueries({ queryKey: ['decisions'] });
      queryClient.invalidateQueries({ queryKey: ['tenders'] });
    },
    onError: () => toast.error('Не удалось одобрить'),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ tenderId, reason, comment }: { tenderId: string; reason: string; comment: string }) =>
      decisionsApi.reject(tenderId, { reason, comment: comment || undefined }),
    onSuccess: () => {
      toast.success('Тендер отклонён');
      setModalState({ type: 'none' });
      queryClient.invalidateQueries({ queryKey: ['decisions'] });
    },
    onError: () => toast.error('Не удалось отклонить'),
  });

  const requestInfoMutation = useMutation({
    mutationFn: ({ tenderId, instructions, returnToStage }: { tenderId: string; instructions: string; returnToStage: string }) =>
      decisionsApi.requestInfo(tenderId, { instructions, return_to_stage: returnToStage }),
    onSuccess: () => {
      toast.success('Запрос отправлен');
      setModalState({ type: 'none' });
      queryClient.invalidateQueries({ queryKey: ['decisions'] });
    },
    onError: () => toast.error('Не удалось отправить запрос'),
  });

  const decisions = decisionsQuery.data || [];
  const totalReady = decisions.length;

  return (
    <div>
      <PageHeader
        title="Решения"
        description={`Готово к подтверждению: ${totalReady}`}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
              <Search className="h-3.5 w-3.5 mr-1.5" />
              Фильтры
            </Button>
            <Button variant="outline" size="sm" onClick={() => decisionsQuery.refetch()}>
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
              <Select value={filters.status} onValueChange={(value) => updateFilters({ status: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="READY_FOR_DECISION">Готовы к решению</SelectItem>
                  <SelectItem value="APPROVED">Одобрены</SelectItem>
                  <SelectItem value="REJECTED">Отклонены</SelectItem>
                  <SelectItem value="NEEDS_MORE_INFO">Требуют уточнения</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Уровень риска</Label>
              <Select value={filters.risk_level || 'all'} onValueChange={(value) => updateFilters({ risk_level: value === 'all' ? '' : value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все</SelectItem>
                  <SelectItem value="LOW">LOW</SelectItem>
                  <SelectItem value="MEDIUM">MEDIUM</SelectItem>
                  <SelectItem value="HIGH">HIGH</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Мин. маржа (%)</Label>
              <Input
                type="number"
                min={0}
                placeholder="0"
                defaultValue={filters.min_margin}
                onChange={(e) => updateFilters({ min_margin: e.target.value })}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Сортировка</Label>
              <Select value={filters.sort_by} onValueChange={(value) => updateFilters({ sort_by: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="margin_percent">По марже</SelectItem>
                  <SelectItem value="deadline_at">По дедлайну</SelectItem>
                  <SelectItem value="created_at">По дате</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button variant="outline" size="sm" onClick={resetFilters}>
              Сбросить
            </Button>
          </div>
        </div>
      )}

      {decisionsQuery.isLoading ? (
        <LoadingSkeleton rows={3} cols={1} type="card" />
      ) : decisionsQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить решения" onRetry={() => decisionsQuery.refetch()} />
      ) : decisions.length === 0 ? (
        <EmptyState
          icon={ClipboardCheck}
          title="Нет решений"
          description="Система продолжает работу. Готовые к подтверждению тендеры появятся здесь."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {decisions.map((decision) => (
            <DecisionCard
              key={decision.tender_id}
              decision={decision}
              onApprove={() => setModalState({ type: 'approve', decision })}
              onReject={() => setModalState({ type: 'reject', decision })}
              onRequestInfo={() => setModalState({ type: 'info', decision })}
              isLoading={approveMutation.isPending || rejectMutation.isPending || requestInfoMutation.isPending}
            />
          ))}
        </div>
      )}

      <ApproveModal
        open={modalState.type === 'approve'}
        onOpenChange={(open) => !open && setModalState({ type: 'none' })}
        decision={modalState.decision as DecisionListItem}
        isLoading={approveMutation.isPending}
        onConfirm={(supplierId, offerId, comment) => {
          if (modalState.decision) {
            approveMutation.mutate({
              tenderId: modalState.decision.tender_id,
              supplierId,
              offerId,
              comment,
            });
          }
        }}
      />
      <RejectModal
        open={modalState.type === 'reject'}
        onOpenChange={(open) => !open && setModalState({ type: 'none' })}
        isLoading={rejectMutation.isPending}
        onConfirm={(reason, comment) => {
          if (modalState.decision) {
            rejectMutation.mutate({
              tenderId: modalState.decision.tender_id,
              reason,
              comment,
            });
          }
        }}
      />
      <RequestInfoModal
        open={modalState.type === 'info'}
        onOpenChange={(open) => !open && setModalState({ type: 'none' })}
        isLoading={requestInfoMutation.isPending}
        onConfirm={(instructions, returnToStage) => {
          if (modalState.decision) {
            requestInfoMutation.mutate({
              tenderId: modalState.decision.tender_id,
              instructions,
              returnToStage,
            });
          }
        }}
      />
    </div>
  );
}