import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Send,
  Clock,
  HelpCircle,
  Wallet,
  RefreshCw,
  Eye,
  type LucideIcon,
} from 'lucide-react';
import { settingsApi } from '../api/settings';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
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
} from '../components/ui/dialog';

const TEMPLATE_CONFIG: Record<string, { label: string; icon: LucideIcon; iconBg: string; iconText: string; description: string }> = {
  cp_request: { label: 'Запрос КП', icon: Send, iconBg: 'bg-blue-100', iconText: 'text-blue-700', description: 'Первичный запрос коммерческого предложения' },
  cp_reminder: { label: 'Напоминание', icon: Clock, iconBg: 'bg-yellow-100', iconText: 'text-yellow-700', description: 'Напоминание о ранее отправленном запросе' },
  clarification: { label: 'Уточнение', icon: HelpCircle, iconBg: 'bg-purple-100', iconText: 'text-purple-700', description: 'Запрос недостающей информации' },
  discount_request: { label: 'Запрос скидки', icon: Wallet, iconBg: 'bg-green-100', iconText: 'text-green-700', description: 'Запрос улучшения ценовых условий' },
};

const ALL_VARIABLES = [
  '{lot_name}', '{positions_table}', '{positions_table_html}', '{positions_table_text}',
  '{total_quantity}', '{deadline_date}', '{nmck}', '{delivery_address}', '{company_name}',
  '{contact_person}', '{contact_email}', '{contact_phone}', '{email_signature}', '{company_signature}',
  '{current_date}', '{clarification_items}', '{discount_positions}',
];

function PreviewModal({ open, onOpenChange, templateKey, subject, body }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  templateKey: string;
  subject: string;
  body: string;
}) {
  const testData: Record<string, string> = {
    '{lot_name}': 'Поставка ноутбуков HP ProBook 450 G10',
    '{positions_table}': '1. Ноутбук HP ProBook — 10 шт\n2. Монитор LG 27UL550 — 10 шт',
    '{positions_table_html}': '<table><tr><td>Ноутбук HP</td><td>10 шт</td></tr></table>',
    '{positions_table_text}': '1. Ноутбук HP ProBook — 10 шт',
    '{total_quantity}': '20',
    '{deadline_date}': '15.10.2026',
    '{nmck}': '1 500 000 ₽',
    '{delivery_address}': 'г. Москва, ул. Примерная, д. 1',
    '{company_name}': 'ООО «Рога и Копыта»',
    '{contact_person}': 'Иван Иванов',
    '{contact_email}': 'ivan@example.com',
    '{contact_phone}': '+7 (999) 123-45-67',
    '{email_signature}': 'С уважением, Иван Иванов',
    '{company_signature}': 'С уважением, Иван Иванов\nООО «Рога и Копыта»\n+7 (999) 123-45-67',
    '{current_date}': new Date().toLocaleDateString('ru-RU'),
    '{clarification_items}': '• Цена на позицию 2\n• Сроки доставки',
    '{discount_positions}': '• Ноутбук HP — конкурент: 82 000 ₽\n• Монитор LG — конкурент: 11 500 ₽',
  };

  const renderTemplate = (text: string): string => {
    let result = text;
    Object.entries(testData).forEach(([key, value]) => {
      result = result.split(key).join(value);
    });
    return result;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Предпросмотр: {TEMPLATE_CONFIG[templateKey]?.label || templateKey}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-xs text-slate-500">Тема</Label>
            <p className="text-sm font-medium text-slate-900 mt-1">{renderTemplate(subject)}</p>
          </div>
          <div>
            <Label className="text-xs text-slate-500">Тело</Label>
            <div className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 rounded-lg p-4 mt-1">{renderTemplate(body)}</div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Закрыть</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function TemplatesPage() {
  const queryClient = useQueryClient();
  const [selectedTemplate, setSelectedTemplate] = useState<string>('cp_request');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [showPreview, setShowPreview] = useState(false);

  const templatesQuery = useQuery({
    queryKey: ['settings', 'templates'],
    queryFn: () => settingsApi.getSection('templates'),
  });

  const saveMutation = useMutation({
    mutationFn: (data: any) => settingsApi.patchSection('templates', data),
    onSuccess: () => {
      toast.success('Шаблон сохранён');
      queryClient.invalidateQueries({ queryKey: ['settings', 'templates'] });
    },
    onError: () => toast.error('Не удалось сохранить'),
  });

  const templates = templatesQuery.data || {};

  useEffect(() => {
    const template = templates[selectedTemplate];
    if (template) {
      setSubject(template.subject || '');
      setBody(template.body || '');
    }
  }, [templates, selectedTemplate]);

  const handleSelectTemplate = (key: string) => {
    setSelectedTemplate(key);
  };

  const handleSave = () => {
    if (!subject.trim() || !body.trim()) {
      toast.error('Тема и тело обязательны');
      return;
    }
    saveMutation.mutate({
      [selectedTemplate]: { subject: subject.trim(), body: body },
    });
  };

  const insertVariable = (variable: string) => {
    setBody((prev) => prev + variable);
  };

  return (
    <div>
      <PageHeader
        title="Шаблоны писем"
        description="Шаблоны для автоматической коммуникации с поставщиками"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowPreview(true)}>
              <Eye className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Предпросмотр
            </Button>
            <Button variant="outline" size="sm" onClick={() => templatesQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Обновить
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
              {saveMutation.isPending ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </>
        }
      />
      {templatesQuery.isLoading ? (
        <LoadingSkeleton rows={3} cols={2} type="card" />
      ) : templatesQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить шаблоны" onRetry={() => templatesQuery.refetch()} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-2">
            {Object.entries(TEMPLATE_CONFIG).map(([key, config]) => {
              const Icon = config.icon;
              const isSelected = selectedTemplate === key;
              return (
                <button
                  key={key}
                  onClick={() => handleSelectTemplate(key)}
                  className={cn(
                    'w-full flex items-start gap-3 rounded-lg border p-3 text-left transition-colors',
                    isSelected ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-white hover:border-slate-300'
                  )}
                >
                  <div className={cn('h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0', config.iconBg)}>
                    <Icon className={cn('h-5 w-5', config.iconText)} aria-hidden="true" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={cn('text-sm font-semibold', isSelected ? 'text-blue-800' : 'text-slate-900')}>{config.label}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{config.description}</p>
                  </div>
                </button>
              );
            })}
          </div>
          <div className="lg:col-span-2 rounded-lg border border-slate-200 bg-white p-4">
            <div className="space-y-4">
              <div>
                <Label>Тема</Label>
                <Input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Запрос КП: {lot_name}" className="mt-1" />
              </div>
              <div>
                <Label>Тело</Label>
                <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={12} className="mt-1 font-mono text-sm" placeholder="Добрый день!" />
              </div>
              <div>
                <Label className="text-xs text-slate-500">Доступные переменные (клик — вставить)</Label>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {ALL_VARIABLES.map((variable) => (
                    <button
                      key={variable}
                      onClick={() => insertVariable(variable)}
                      className="rounded-md bg-slate-100 px-2 py-1 text-xs font-mono text-slate-600 hover:bg-blue-100 hover:text-blue-700 transition-colors cursor-pointer"
                    >
                      {variable}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      <PreviewModal open={showPreview} onOpenChange={setShowPreview} templateKey={selectedTemplate} subject={subject} body={body} />
    </div>
  );
}