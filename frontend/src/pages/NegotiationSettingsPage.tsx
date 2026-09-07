import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { RefreshCw, Save, Mail, Send, Phone, Globe, CheckCircle2, type LucideIcon } from 'lucide-react';
import { settingsApi } from '../api/settings';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
import { cn } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const CHANNEL_CONFIG: Record<string, { label: string; icon: LucideIcon }> = {
  email: { label: 'Email', icon: Mail },
  telegram: { label: 'Telegram', icon: Send },
  whatsapp: { label: 'WhatsApp', icon: Phone },
  web_form: { label: 'Форма на сайте', icon: Globe },
};

export function NegotiationSettingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    max_clarification_cycles: '2',
    max_discount_requests_per_supplier: '2',
    price_diff_threshold_percent: '5.0',
    response_timeout_hours: '48',
    reminder_after_hours: '24',
    max_suppliers_per_lot: '10',
  });
  const [channelPriority, setChannelPriority] = useState<string[]>(['email', 'telegram', 'whatsapp', 'web_form']);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const communicationQuery = useQuery({
    queryKey: ['settings', 'communication'],
    queryFn: () => settingsApi.getSection('communication'),
  });

  useEffect(() => {
    if (communicationQuery.data) {
      const data = communicationQuery.data;
      setForm({
        max_clarification_cycles: String(data.max_clarification_cycles ?? 2),
        max_discount_requests_per_supplier: String(data.max_discount_requests_per_supplier ?? 2),
        price_diff_threshold_percent: String(data.price_diff_threshold_percent ?? 5.0),
        response_timeout_hours: String(data.response_timeout_hours ?? 48),
        reminder_after_hours: String(data.reminder_after_hours ?? 24),
        max_suppliers_per_lot: String(data.max_suppliers_per_lot ?? 10),
      });
      if (data.channel_priority && Array.isArray(data.channel_priority) && data.channel_priority.length > 0) {
        setChannelPriority(data.channel_priority);
      }
    }
  }, [communicationQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (data: any) => settingsApi.putSection('communication', data),
    onSuccess: () => {
      toast.success('Настройки переговоров сохранены');
      queryClient.invalidateQueries({ queryKey: ['settings', 'communication'] });
    },
    onError: () => toast.error('Не удалось сохранить'),
  });

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    const integerFields = ['max_clarification_cycles','max_discount_requests_per_supplier','response_timeout_hours','reminder_after_hours','max_suppliers_per_lot'];
    integerFields.forEach((field) => {
      const value = Number(form[field as keyof typeof form]);
      if (isNaN(value) || value < 0 || !Number.isInteger(value)) newErrors[field] = 'Должно быть целым неотрицательным числом';
    });
    const priceDiff = Number(form.price_diff_threshold_percent);
    if (isNaN(priceDiff) || priceDiff < 0 || priceDiff > 100) newErrors.price_diff_threshold_percent = 'Должно быть 0-100';
    if (Number(form.reminder_after_hours) >= Number(form.response_timeout_hours)) newErrors.reminder_after_hours = 'Должно быть меньше таймаута';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;
    saveMutation.mutate({
      max_clarification_cycles: Number(form.max_clarification_cycles),
      max_discount_requests_per_supplier: Number(form.max_discount_requests_per_supplier),
      price_diff_threshold_percent: Number(form.price_diff_threshold_percent),
      response_timeout_hours: Number(form.response_timeout_hours),
      reminder_after_hours: Number(form.reminder_after_hours),
      max_suppliers_per_lot: Number(form.max_suppliers_per_lot),
      channel_priority: channelPriority,
    });
  };

  const moveChannel = (index: number, direction: 'up' | 'down') => {
    const newPriority = [...channelPriority];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= newPriority.length) return;
    [newPriority[index], newPriority[targetIndex]] = [newPriority[targetIndex], newPriority[index]];
    setChannelPriority(newPriority);
  };

  if (communicationQuery.isLoading) return <LoadingSkeleton rows={5} cols={2} type="form" />;
  if (communicationQuery.isError) return <ErrorAlert message="Не удалось загрузить настройки" onRetry={() => communicationQuery.refetch()} />;

  const integerFields = [
    { key: 'max_clarification_cycles', label: 'Максимум циклов уточнений' },
    { key: 'max_discount_requests_per_supplier', label: 'Максимум запросов скидки на одного поставщика' },
    { key: 'response_timeout_hours', label: 'Таймаут ожидания ответа (часов)' },
    { key: 'reminder_after_hours', label: 'Напоминание через (часов)' },
    { key: 'max_suppliers_per_lot', label: 'Максимум поставщиков на один лот' },
  ];

  return (
    <div>
      <PageHeader
        title="Переговоры"
        description="Стратегия автоматических переговоров с поставщиками"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => communicationQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Сбросить
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
              <Save className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              {saveMutation.isPending ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </>
        }
      />
      <div className="space-y-6 max-w-2xl">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-4">Циклы и таймауты</h3>
          <div className="space-y-4">
            {integerFields.map((field) => (
              <div key={field.key}>
                <Label>{field.label}</Label>
                <Input type="number" min={0} step={1} value={form[field.key as keyof typeof form]} onChange={(e) => setForm({ ...form, [field.key]: e.target.value })} className={cn('mt-1', errors[field.key] && 'border-red-300')} />
                {errors[field.key] && <p className="text-xs text-red-600 mt-1">{errors[field.key]}</p>}
              </div>
            ))}
            <div>
              <Label>Порог разницы в цене для запроса скидки (%)</Label>
              <Input type="number" min={0} max={100} step={0.1} value={form.price_diff_threshold_percent} onChange={(e) => setForm({ ...form, price_diff_threshold_percent: e.target.value })} className={cn('mt-1', errors.price_diff_threshold_percent && 'border-red-300')} />
              {errors.price_diff_threshold_percent && <p className="text-xs text-red-600 mt-1">{errors.price_diff_threshold_percent}</p>}
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-2">Приоритет каналов связи</h3>
          <p className="text-sm text-slate-500 mb-4">Каналы будут использоваться в указанном порядке. Перемещайте стрелками.</p>
          <div className="space-y-2">
            {channelPriority.map((channel, index) => {
              const config = CHANNEL_CONFIG[channel] || { label: channel, icon: Mail };
              const Icon = config.icon;
              return (
                <div key={channel} className="flex items-center gap-3 rounded-lg border border-slate-200 p-3 bg-white">
                  <span className="text-sm font-medium text-slate-400 w-6">{index + 1}.</span>
                  <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center"><Icon className="h-4 w-4 text-slate-500" aria-hidden="true" /></div>
                  <span className="text-sm font-medium text-slate-900 flex-1">{config.label}</span>
                  <button type="button" onClick={() => moveChannel(index, 'up')} disabled={index === 0} className="p-1 rounded-md text-slate-400 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed" aria-label="Вверх">↑</button>
                  <button type="button" onClick={() => moveChannel(index, 'down')} disabled={index === channelPriority.length - 1} className="p-1 rounded-md text-slate-400 hover:bg-slate-100 disabled:opacity-30 disabled:cursor-not-allowed" aria-label="Вниз">↓</button>
                </div>
              );
            })}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-green-600" aria-hidden="true" />
          <span className="text-sm text-slate-600">При сохранении система применит настройки ко всем будущим переговорам</span>
        </div>
      </div>
    </div>
  );
}