import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Play, RefreshCw, Send, Check, XCircle, Clock, Loader2, Mail } from 'lucide-react';
import { tendersApi } from '../../api/tenders';
import { Button } from '../ui/button';
import { Checkbox } from '../ui/checkbox';

interface PipelineStepsResponse {
  task_id: string | null;
  status: string | null;
  progress_percent: number;
  steps: Array<{
    step: string;
    status: string;
    percent: number;
    error?: string;
  }>;
  result_summary: string | null;
  error_message: string | null;
}

interface Draft {
  id: string;
  supplier_website: string;
  supplier_name: string;
  email: string;
  subject: string;
  body_text: string;
  status: string;
  created_at: string | null;
}

const PIPELINE_STEP_LABELS: Record<string, string> = {
  PROCESS_TENDER: '1. Обработка тендера',
  GENERATE_QUERIES: '2. Генерация запросов',
  SEARCH_SUPPLIERS: '3. Поиск поставщиков',
  CRAWL_EMAILS: '4. Поиск email на сайтах',
  CREATE_DRAFTS: '5. Создание черновиков писем',
};

export function TenderPipelineTab({ tenderId, tenderStatus }: { tenderId: string; tenderStatus: string }) {
  const [selectedDrafts, setSelectedDrafts] = useState<string[]>([]);
  const [sending, setSending] = useState(false);
  const [launching, setLaunching] = useState(false);

  const stepsQuery = useQuery({
    queryKey: ['pipeline-steps', tenderId],
    queryFn: () => tendersApi.getPipelineSteps(tenderId),
    refetchInterval: (query) => {
      const data = query.state.data as PipelineStepsResponse | undefined;
      if (data?.status === 'IN_PROGRESS' || data?.status === 'PENDING') return 3000;
      return false;
    },
    enabled: !!tenderId,
  });

  const draftsQuery = useQuery({
    queryKey: ['drafts', tenderId],
    queryFn: () => tendersApi.listDrafts(tenderId),
    enabled: !!tenderId,
  });

  const pipelineSteps = stepsQuery.data as PipelineStepsResponse | null;
  const draftsResponse = draftsQuery.data as { drafts?: Draft[] } | null;
  const drafts = draftsResponse?.drafts || [];

  const handleRunPipeline = async () => {
    setLaunching(true);
    try {
      await tendersApi.runPipeline(tenderId);
      toast.success('Конвейер запущен. Следите за прогрессом.');
      stepsQuery.refetch();
    } catch {
      toast.error('Не удалось запустить конвейер');
    } finally {
      setLaunching(false);
    }
  };

  const handleSendSelected = async () => {
    if (selectedDrafts.length === 0) return;
    setSending(true);
    try {
      await tendersApi.sendDrafts(tenderId, selectedDrafts);
      toast.success(`Отправлено писем: ${selectedDrafts.length}`);
      setSelectedDrafts([]);
      draftsQuery.refetch();
    } catch {
      toast.error('Не удалось отправить письма');
    } finally {
      setSending(false);
    }
  };

  const toggleDraft = (draftId: string) => {
    setSelectedDrafts((prev) =>
      prev.includes(draftId) ? prev.filter((id) => id !== draftId) : [...prev, draftId]
    );
  };

  const selectAllDrafts = () => {
    const draftIds = drafts.filter((d) => d.status === 'draft').map((d) => d.id);
    setSelectedDrafts(draftIds);
  };

  const clearSelection = () => setSelectedDrafts([]);

  const stepList = pipelineSteps?.steps || [];
  const isRunning = pipelineSteps?.status === 'IN_PROGRESS' || pipelineSteps?.status === 'PENDING';

  const progress = Math.round(pipelineSteps?.progress_percent || 0);

  return (
    <div className="space-y-6">
      {/* Pipeline Launch Card */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-4">
          <h3 className="text-base font-semibold text-slate-900">Автоматический конвейер поставщиков</h3>
          <p className="text-sm text-slate-500 mt-0.5">Обрабатывает тендер, ищет поставщиков, собирает email'ы и готовит черновики писем.</p>
        </div>
        <div className="px-5 py-4">
          <p className="text-sm text-slate-500 mb-3">Статус тендера: {tenderStatus}</p>
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={handleRunPipeline} disabled={launching || isRunning} className="gap-2">
              {launching || isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Play className="h-4 w-4" aria-hidden="true" />
              )}
              {launching || isRunning ? 'Запуск/Выполняется...' : 'Запустить полный конвейер'}
            </Button>
            <Button variant="outline" onClick={() => stepsQuery.refetch()} disabled={isRunning} className="gap-2">
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Обновить
            </Button>
          </div>

          {(isRunning || progress > 0) && (
            <div className="mt-4">
              <div className="w-full bg-slate-200 rounded-full h-2 mb-1">
                <div className="bg-blue-600 h-2 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
              </div>
              <p className="text-sm text-slate-600">Прогресс: {progress}%</p>
            </div>
          )}

          {stepList.length > 0 && (
            <div className="mt-4 space-y-2">
              {stepList.map((step) => {
                const label = PIPELINE_STEP_LABELS[step.step] || step.step;
                let icon;
                let colorClass;
                if (step.status === 'ERROR') {
                  icon = <XCircle className="h-4 w-4 text-red-500" />;
                  colorClass = 'border-red-200 bg-red-50';
                } else if (step.status === 'COMPLETED') {
                  icon = <Check className="h-4 w-4 text-green-600" />;
                  colorClass = 'border-green-200 bg-green-50';
                } else if (step.status === 'IN_PROGRESS') {
                  icon = <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
                  colorClass = 'border-blue-200 bg-blue-50';
                } else {
                  icon = <Clock className="h-4 w-4 text-slate-400" />;
                  colorClass = 'border-slate-200 bg-slate-50';
                }
                return (
                  <div key={step.step} className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${colorClass} text-sm`}>
                    {icon}
                    <span className="flex-1 font-medium">{label}</span>
                    <span className="text-xs text-slate-500">
                      {step.status === 'ERROR' ? step.error || 'Ошибка' : `${step.percent}%`}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {pipelineSteps?.result_summary && !isRunning && (
            <p className="mt-3 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
              {pipelineSteps.result_summary}
            </p>
          )}
          {pipelineSteps?.error_message && !isRunning && pipelineSteps.status === 'FAILED' && (
            <p className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {pipelineSteps.error_message}
            </p>
          )}
        </div>
      </div>

      {/* Drafts Card */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="border-b border-slate-200 px-5 py-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <h3 className="text-base font-semibold text-slate-900">Черновики писем поставщикам</h3>
              <p className="text-sm text-slate-500 mt-0.5">Выберите отправления и отправьте одним нажатием.</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={selectAllDrafts} className="text-xs">
                Выбрать
              </Button>
              <Button variant="outline" size="sm" onClick={clearSelection} className="text-xs">
                Сбросить
              </Button>
              <Button
                size="sm"
                onClick={handleSendSelected}
                disabled={sending || selectedDrafts.length === 0}
                className="gap-1.5"
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
                Отправить ({selectedDrafts.length})
              </Button>
            </div>
          </div>
        </div>
        <div className="px-5 py-4">
          {drafts.length === 0 ? (
            <div className="py-8 text-center">
              <Mail className="h-8 w-8 text-slate-300 mx-auto mb-2" aria-hidden="true" />
              <p className="text-sm text-slate-500">Черновики ещё не созданы. Запустите полный конвейер.</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {drafts.map((draft) => {
                const isChecked = selectedDrafts.includes(draft.id);
                const isSent = draft.status === 'sent';
                return (
                  <div key={draft.id} className={`p-3 border rounded-lg ${isSent ? 'opacity-60 bg-slate-50' : 'hover:bg-slate-50'}`}>
                    <div className="flex items-start gap-3">
                      <Checkbox
                        checked={isChecked}
                        onCheckedChange={() => toggleDraft(draft.id)}
                        disabled={isSent}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-semibold truncate">
                            {draft.supplier_name || 'Поставщик не указан'}
                            {isSent && <span className="ml-2 text-green-600 text-xs font-normal">✓ Отправлено</span>}
                          </span>
                          <span className="text-xs text-slate-500">{draft.email}</span>
                        </div>
                        <p className="text-sm font-medium text-slate-800">{draft.subject}</p>
                        <p className="text-sm text-slate-600 line-clamp-2 mt-1 whitespace-pre-wrap">{draft.body_text}</p>
                        {draft.supplier_website && (
                          <a href={draft.supplier_website} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline break-all mt-1 block">
                            {draft.supplier_website}
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
