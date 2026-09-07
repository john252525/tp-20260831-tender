import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { RefreshCw, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import { settingsApi } from '../api/settings';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
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

export function ScoringPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    min_total_score: '60',
    min_margin_percent: '15.0',
    max_risk_level: 'MEDIUM',
    weight_margin: '40',
    weight_simplicity: '30',
    weight_volume: '20',
    weight_competition: '10',
    volume_low: '100000',
    volume_medium: '1000000',
    volume_high: '5000000',
    score_low: '20',
    score_medium: '50',
    score_high: '80',
    score_very_high: '95',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const scoringQuery = useQuery({
    queryKey: ['settings', 'scoring'],
    queryFn: () => settingsApi.getSection('scoring'),
  });

  useEffect(() => {
    if (scoringQuery.data) {
      const data = scoringQuery.data;
      setForm({
        min_total_score: String(data.min_total_score ?? 60),
        min_margin_percent: String(data.min_margin_percent ?? 15.0),
        max_risk_level: data.max_risk_level || 'MEDIUM',
        weight_margin: String(data.weight_margin ?? 40),
        weight_simplicity: String(data.weight_simplicity ?? 30),
        weight_volume: String(data.weight_volume ?? 20),
        weight_competition: String(data.weight_competition ?? 10),
        volume_low: String(data.volume_thresholds?.low ?? 100000),
        volume_medium: String(data.volume_thresholds?.medium ?? 1000000),
        volume_high: String(data.volume_thresholds?.high ?? 5000000),
        score_low: String(data.volume_scores?.low ?? 20),
        score_medium: String(data.volume_scores?.medium ?? 50),
        score_high: String(data.volume_scores?.high ?? 80),
        score_very_high: String(data.volume_scores?.very_high ?? 95),
      });
    }
  }, [scoringQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (data: any) => settingsApi.putSection('scoring', data),
    onSuccess: () => {
      toast.success('Настройки скоринга сохранены');
      queryClient.invalidateQueries({ queryKey: ['settings', 'scoring'] });
    },
    onError: () => toast.error('Не удалось сохранить'),
  });

  const weightsSum =
    Number(form.weight_margin) +
    Number(form.weight_simplicity) +
    Number(form.weight_volume) +
    Number(form.weight_competition);
  const isWeightsValid = weightsSum === 100;

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (Number(form.min_total_score) < 0 || Number(form.min_total_score) > 100) {
      newErrors.min_total_score = 'Должно быть 0-100';
    }
    if (Number(form.min_margin_percent) < 0 || Number(form.min_margin_percent) > 100) {
      newErrors.min_margin_percent = 'Должно быть 0-100';
    }
    if (!isWeightsValid) {
      newErrors.weights = `Сумма весов должна быть 100% (сейчас: ${weightsSum}%)`;
    }
    ['weight_margin', 'weight_simplicity', 'weight_volume', 'weight_competition'].forEach((key) => {
      const val = Number(form[key as keyof typeof form]);
      if (val < 0 || val > 100) newErrors[key] = 'Должно быть 0-100';
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;
    saveMutation.mutate({
      min_total_score: Number(form.min_total_score),
      min_margin_percent: Number(form.min_margin_percent),
      max_risk_level: form.max_risk_level,
      weight_margin: Number(form.weight_margin),
      weight_simplicity: Number(form.weight_simplicity),
      weight_volume: Number(form.weight_volume),
      weight_competition: Number(form.weight_competition),
      volume_thresholds: { low: Number(form.volume_low), medium: Number(form.volume_medium), high: Number(form.volume_high) },
      volume_scores: { low: Number(form.score_low), medium: Number(form.score_medium), high: Number(form.score_high), very_high: Number(form.score_very_high) },
    });
  };

  const handleReset = () => scoringQuery.refetch();

  if (scoringQuery.isLoading) return <LoadingSkeleton rows={5} cols={2} type="form" />;
  if (scoringQuery.isError) return <ErrorAlert message="Не удалось загрузить настройки" onRetry={() => scoringQuery.refetch()} />;

  return (
    <div>
      <PageHeader
        title="Скоринг"
        description="Параметры оценки привлекательности тендеров"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={handleReset}>
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
          <h3 className="text-base font-semibold text-slate-900 mb-4">Пороги</h3>
          <div className="space-y-4">
            <div>
              <Label>Минимальный скор тендера (0-100)</Label>
              <Input type="number" min={0} max={100} value={form.min_total_score} onChange={(e) => setForm({ ...form, min_total_score: e.target.value })} className={cn('mt-1', errors.min_total_score && 'border-red-300')} />
              {errors.min_total_score && <p className="text-xs text-red-600 mt-1">{errors.min_total_score}</p>}
            </div>
            <div>
              <Label>Минимальная маржа (%)</Label>
              <Input type="number" min={0} max={100} step={0.1} value={form.min_margin_percent} onChange={(e) => setForm({ ...form, min_margin_percent: e.target.value })} className={cn('mt-1', errors.min_margin_percent && 'border-red-300')} />
              {errors.min_margin_percent && <p className="text-xs text-red-600 mt-1">{errors.min_margin_percent}</p>}
            </div>
            <div>
              <Label>Максимальный уровень риска для авто-одобрения</Label>
              <Select value={form.max_risk_level} onValueChange={(value) => setForm({ ...form, max_risk_level: value })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="LOW">LOW (только низкий)</SelectItem>
                  <SelectItem value="MEDIUM">MEDIUM (низкий и средний)</SelectItem>
                  <SelectItem value="HIGH">HIGH (все)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-2">Веса компонентов</h3>
          <p className="text-sm text-slate-500 mb-4">Сумма всех весов должна быть равна 100%</p>
          <div className={cn('rounded-lg p-3 mb-4 flex items-center gap-2', isWeightsValid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200')}>
            {isWeightsValid ? <CheckCircle2 className="h-4 w-4 text-green-600" aria-hidden="true" /> : <AlertCircle className="h-4 w-4 text-red-600" aria-hidden="true" />}
            <span className={cn('text-sm font-medium', isWeightsValid ? 'text-green-700' : 'text-red-700')}>
              Сумма весов: {weightsSum}% {isWeightsValid ? '✓' : '— должно быть 100%'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label>Маржинальность (%)</Label>
              <Input type="number" min={0} max={100} value={form.weight_margin} onChange={(e) => setForm({ ...form, weight_margin: e.target.value })} className={cn('mt-1', errors.weight_margin && 'border-red-300')} />
              {errors.weight_margin && <p className="text-xs text-red-600 mt-1">{errors.weight_margin}</p>}
            </div>
            <div>
              <Label>Простота (%)</Label>
              <Input type="number" min={0} max={100} value={form.weight_simplicity} onChange={(e) => setForm({ ...form, weight_simplicity: e.target.value })} className={cn('mt-1', errors.weight_simplicity && 'border-red-300')} />
              {errors.weight_simplicity && <p className="text-xs text-red-600 mt-1">{errors.weight_simplicity}</p>}
            </div>
            <div>
              <Label>Объём (%)</Label>
              <Input type="number" min={0} max={100} value={form.weight_volume} onChange={(e) => setForm({ ...form, weight_volume: e.target.value })} className={cn('mt-1', errors.weight_volume && 'border-red-300')} />
              {errors.weight_volume && <p className="text-xs text-red-600 mt-1">{errors.weight_volume}</p>}
            </div>
            <div>
              <Label>Конкуренция (%)</Label>
              <Input type="number" min={0} max={100} value={form.weight_competition} onChange={(e) => setForm({ ...form, weight_competition: e.target.value })} className={cn('mt-1', errors.weight_competition && 'border-red-300')} />
              {errors.weight_competition && <p className="text-xs text-red-600 mt-1">{errors.weight_competition}</p>}
            </div>
          </div>
          {errors.weights && <p className="text-xs text-red-600 mt-2">{errors.weights}</p>}
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-4">Пороги объёма (НМЦК)</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div>
              <Label>Низкий (&lt;, ₽)</Label>
              <Input type="number" min={0} value={form.volume_low} onChange={(e) => setForm({ ...form, volume_low: e.target.value })} className="mt-1" />
            </div>
            <div>
              <Label>Средний (&lt;, ₽)</Label>
              <Input type="number" min={0} value={form.volume_medium} onChange={(e) => setForm({ ...form, volume_medium: e.target.value })} className="mt-1" />
            </div>
            <div>
              <Label>Высокий (&lt;, ₽)</Label>
              <Input type="number" min={0} value={form.volume_high} onChange={(e) => setForm({ ...form, volume_high: e.target.value })} className="mt-1" />
            </div>
          </div>
          <p className="text-xs text-slate-500 mb-3">Скоры для каждого уровня объёма:</p>
          <div className="grid grid-cols-4 gap-4">
            <div><Label>Низкий</Label><Input type="number" min={0} max={100} value={form.score_low} onChange={(e) => setForm({ ...form, score_low: e.target.value })} className="mt-1" /></div>
            <div><Label>Средний</Label><Input type="number" min={0} max={100} value={form.score_medium} onChange={(e) => setForm({ ...form, score_medium: e.target.value })} className="mt-1" /></div>
            <div><Label>Высокий</Label><Input type="number" min={0} max={100} value={form.score_high} onChange={(e) => setForm({ ...form, score_high: e.target.value })} className="mt-1" /></div>
            <div><Label>Очень высокий</Label><Input type="number" min={0} max={100} value={form.score_very_high} onChange={(e) => setForm({ ...form, score_very_high: e.target.value })} className="mt-1" /></div>
          </div>
        </div>
      </div>
    </div>
  );
}