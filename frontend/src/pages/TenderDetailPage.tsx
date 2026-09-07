import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  RefreshCw,
  Play,
  Search,
  Send,
  MessagesSquare,
  CheckCircle2,
  XCircle,
  ClipboardCheck,
  Download,
  ExternalLink,
  Loader2,
  FileText,
  FileSpreadsheet,
  Archive,
  FileImage,
  File,
  Eye,
  Users,
  Plus,
  ChevronDown,
  ChevronUp,
  Wallet,
  Building2,
  UserPlus,
  Inbox,
  Circle,
  AlertCircle,
  type LucideIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { tendersApi, type TenderDetail, type TenderDocument, type LotSupplier, type TenderTimelineEvent } from '../api/tenders';
import { commercialOffersApi } from '../api/commercialOffers';
import { suppliersApi } from '../api/suppliers';
import { StatusBadge } from '../components/common/StatusBadge';
import { ScoreBadge } from '../components/common/ScoreBadge';
import { TypeBadge } from '../components/common/TypeBadge';
import { ProgressBar } from '../components/common/ProgressBar';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { formatMoney, formatDate, formatDateTime } from '../lib/formatters';
import { cn } from '../lib/utils';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Button } from '../components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Checkbox } from '../components/ui/checkbox';

// ============================================================
// Вкладка «Обзор»
// ============================================================
function TenderOverviewTab({ tender }: { tender: TenderDetail }) {
  const scoreComponents = tender?.score_components;
  const requirements = tender?.structured_data?.requirements;
  const sourceInfo = tender?.source;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-base font-semibold text-slate-900 mb-4">Основная информация</h3>
        <dl className="space-y-3">
          <div>
            <dt className="text-xs text-slate-500">ID</dt>
            <dd className="text-sm text-slate-900 font-mono truncate">{tender?.id}</dd>
          </div>
          {sourceInfo && (
            <div>
              <dt className="text-xs text-slate-500">Источник</dt>
              <dd className="text-sm text-slate-900">{sourceInfo.name}</dd>
            </div>
          )}
          <div>
            <dt className="text-xs text-slate-500">Заказчик</dt>
            <dd className="text-sm text-slate-900">{tender?.customer_name || '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">ИНН</dt>
            <dd className="text-sm text-slate-900">{tender?.customer_inn || '—'}</dd>
          </div>
          {tender?.customer_kpp && (
            <div>
              <dt className="text-xs text-slate-500">КПП</dt>
              <dd className="text-sm text-slate-900">{tender.customer_kpp}</dd>
            </div>
          )}
          <div>
            <dt className="text-xs text-slate-500">Площадка</dt>
            <dd className="text-sm text-slate-900">{tender?.platform || '—'}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Опубликован</dt>
            <dd className="text-sm text-slate-900">{formatDate(tender?.published_at)}</dd>
          </div>
          <div>
            <dt className="text-xs text-slate-500">Дедлайн подачи</dt>
            <dd className="text-sm text-slate-900 font-medium">{formatDate(tender?.deadline_at)}</dd>
          </div>
          {tender?.source_url && (
            <div>
              <dt className="text-xs text-slate-500">Ссылка</dt>
              <dd>
                <a
                  href={tender.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                >
                  Открыть оригинал
                  <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                </a>
              </dd>
            </div>
          )}
        </dl>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-base font-semibold text-slate-900 mb-4">Требования</h3>
        {requirements ? (
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-slate-500">Дедлайн поставки</dt>
              <dd className="text-sm text-slate-900">{formatDate(requirements.delivery_date)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Адрес поставки</dt>
              <dd className="text-sm text-slate-900">{requirements.delivery_address || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Условия доставки</dt>
              <dd className="text-sm text-slate-900">{requirements.delivery_conditions || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Лицензия</dt>
              <dd className="text-sm text-slate-900">{requirements.license_required ? 'Да' : 'Нет'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">СРО</dt>
              <dd className="text-sm text-slate-900">{requirements.sro_required ? 'Да' : 'Нет'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Обеспечение заявки</dt>
              <dd className="text-sm text-slate-900">{formatMoney(requirements.security_bid)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Обеспечение контракта</dt>
              <dd className="text-sm text-slate-900">{formatMoney(requirements.security_contract)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Аванс</dt>
              <dd className="text-sm text-slate-900">
                {requirements.prepayment_percent !== null && requirements.prepayment_percent !== undefined
                  ? `${requirements.prepayment_percent}%`
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Этапы</dt>
              <dd className="text-sm text-slate-900">{requirements.stages_count || 1}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-slate-400">Требования не извлечены</p>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-base font-semibold text-slate-900 mb-4">Скоринг</h3>
        {scoreComponents ? (
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-slate-600">Маржинальность</span>
                <span className="text-sm font-medium text-slate-900">{scoreComponents.margin_score}/100</span>
              </div>
              <ProgressBar value={scoreComponents.margin_score} size="md" />
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-slate-600">Простота</span>
                <span className="text-sm font-medium text-slate-900">{scoreComponents.simplicity_score}/100</span>
              </div>
              <ProgressBar value={scoreComponents.simplicity_score} size="md" />
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-slate-600">Объём</span>
                <span className="text-sm font-medium text-slate-900">{scoreComponents.volume_score}/100</span>
              </div>
              <ProgressBar value={scoreComponents.volume_score} size="md" />
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-sm text-slate-600">Конкуренция</span>
                <span className="text-sm font-medium text-slate-900">{scoreComponents.competition_score}/100</span>
              </div>
              <ProgressBar value={scoreComponents.competition_score} size="md" />
            </div>
            <div className="pt-3 border-t border-slate-100">
              <div className="flex justify-between mb-1">
                <span className="text-sm font-semibold text-slate-900">ИТОГО</span>
                <span className="text-sm font-semibold text-slate-900">{tender?.score}/100</span>
              </div>
              <ProgressBar value={tender?.score || 0} size="lg" showLabel />
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-400">Скоринг не выполнен</p>
        )}
      </div>
    </div>
  );
}

// ============================================================
// Вкладка «Позиции»
// ============================================================
function TenderPositionsTab({ positions }: { positions: any[] }) {
  const handleExport = () => {
    if (!positions || positions.length === 0) return;
    const headers = ['№', 'Наименование', 'Характеристики', 'ГОСТ', 'ОКПД2', 'Количество', 'Ед.', 'Критичность'];
    const rows = positions.map((p: any) => [
      p.position_number,
      p.name,
      p.characteristics,
      p.gost,
      p.okpd2,
      p.quantity,
      p.unit,
      p.is_essential ? 'Да' : 'Нет',
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'positions.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  if (!positions || positions.length === 0) {
    return <EmptyState title="Позиции не найдены" description="Структурированные данные ещё не извлечены" />;
  }

  return (
    <div>
      <div className="flex justify-end mb-3">
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
          Экспорт CSV
        </Button>
      </div>
      <div className="rounded-lg border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">№</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Наименование</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Характеристики</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">ГОСТ</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">ОКПД2</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Кол-во</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Ед.</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Критичность</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((position: any) => (
              <tr key={position.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-3 text-slate-600">{position.position_number}</td>
                <td className="px-4 py-3 font-medium text-slate-900">{position.name}</td>
                <td className="px-4 py-3 text-slate-600 max-w-[300px] truncate">{position.characteristics || '—'}</td>
                <td className="px-4 py-3 text-slate-600">{position.gost || '—'}</td>
                <td className="px-4 py-3 text-slate-600 text-xs font-mono">{position.okpd2 || '—'}</td>
                <td className="px-4 py-3 text-right text-slate-900">{position.quantity}</td>
                <td className="px-4 py-3 text-slate-600">{position.unit}</td>
                <td className="px-4 py-3">
                  {position.is_essential ? (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-semibold text-red-700">
                      КРИТИЧНАЯ
                    </span>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// Вкладка «Документы»
// ============================================================
function TenderDocumentsTab({ documents }: { documents: TenderDocument[] }) {
  const [previewDoc, setPreviewDoc] = useState<TenderDocument | null>(null);

  const getFileIcon = (doc: TenderDocument) => {
    const { mime_type, filename } = doc;
    if (mime_type === 'application/pdf' || filename.endsWith('.pdf')) return <FileText className="h-8 w-8 text-red-500" aria-hidden="true" />;
    if (mime_type.includes('word') || filename.endsWith('.docx') || filename.endsWith('.doc')) return <FileText className="h-8 w-8 text-blue-500" aria-hidden="true" />;
    if (mime_type.includes('excel') || mime_type.includes('spreadsheet') || filename.endsWith('.xlsx') || filename.endsWith('.xls')) return <FileSpreadsheet className="h-8 w-8 text-green-600" aria-hidden="true" />;
    if (filename.endsWith('.zip') || filename.endsWith('.rar')) return <Archive className="h-8 w-8 text-yellow-600" aria-hidden="true" />;
    if (mime_type.startsWith('image/')) return <FileImage className="h-8 w-8 text-purple-500" aria-hidden="true" />;
    return <File className="h-8 w-8 text-slate-400" aria-hidden="true" />;
  };

  if (!documents || documents.length === 0) {
    return <EmptyState title="Документы не найдены" description="Документация тендера ещё не загружена" />;
  }

  return (
    <div className="space-y-3">
      {documents.map((doc) => (
        <div key={doc.id} className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-start gap-3">
            {getFileIcon(doc)}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-slate-900 truncate">{doc.filename}</p>
                {doc.parse_status === 'PARSED' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700">
                    <CheckCircle2 className="h-3 w-3" aria-hidden="true" />PARSED
                  </span>
                )}
                {doc.parse_status === 'PARSING' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                    <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />PARSING
                  </span>
                )}
                {doc.parse_status === 'ERROR' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700">
                    <XCircle className="h-3 w-3" aria-hidden="true" />ERROR
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">{(doc.file_size_bytes / 1024 / 1024).toFixed(2)} MB</p>
              {doc.parsed_text_preview && <p className="text-xs text-slate-500 mt-2 line-clamp-3">{doc.parsed_text_preview}</p>}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {doc.parsed_text_preview && (
                <Button variant="outline" size="sm" onClick={() => setPreviewDoc(doc)}>
                  <Eye className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Предпросмотр
                </Button>
              )}
              {doc.source_url && (
                <Button variant="outline" size="sm" onClick={() => window.open(doc.source_url, '_blank')}>
                  <Download className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Скачать
                </Button>
              )}
            </div>
          </div>
        </div>
      ))}

      <Dialog open={!!previewDoc} onOpenChange={(open) => !open && setPreviewDoc(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{previewDoc?.filename}</DialogTitle>
            <DialogDescription>
              {previewDoc ? `${(previewDoc.file_size_bytes / 1024).toFixed(0)} KB | Извлечённый текст` : ''}
            </DialogDescription>
          </DialogHeader>
          <div className="whitespace-pre-wrap text-sm text-slate-700 font-mono bg-slate-50 rounded-lg p-4 max-h-[50vh] overflow-y-auto">
            {previewDoc?.parsed_text_preview || 'Текст не извлечён'}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================
// Вкладка «Поставщики»
// ============================================================
function TenderSuppliersTab({
  tenderId,
  lotSuppliers,
  onRefresh,
}: {
  tenderId: string;
  lotSuppliers: LotSupplier[];
  onRefresh: () => void;
}) {
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [showManualModal, setShowManualModal] = useState(false);
  const [selectedSuppliers, setSelectedSuppliers] = useState<Record<string, boolean>>({});

  const searchResultsQuery = useQuery({
    queryKey: ['tender', tenderId, 'supplier-search'],
    queryFn: () => tendersApi.getSupplierSearchResults(tenderId),
    enabled: showSearchModal,
  });

  const handleConfirmSuppliers = async () => {
    const supplierIds = Object.keys(selectedSuppliers).filter((id) => selectedSuppliers[id]);
    if (supplierIds.length === 0) {
      toast.error('Выберите хотя бы одного поставщика');
      return;
    }
    try {
      await tendersApi.confirmSuppliers(tenderId, { supplier_ids: supplierIds });
      toast.success(`Добавлено поставщиков: ${supplierIds.length}`);
      setShowSearchModal(false);
      setSelectedSuppliers({});
      onRefresh();
    } catch {
      toast.error('Не удалось добавить поставщиков');
    }
  };

  if (lotSuppliers.length === 0) {
    return (
      <div>
        <div className="flex justify-end mb-3 gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowSearchModal(true)}>
            <Search className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Добавить из поиска
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowManualModal(true)}>
            <Plus className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Создать вручную
          </Button>
        </div>
        <EmptyState icon={Users} title="Поставщики не привязаны" description="Запустите поиск поставщиков или добавьте вручную" />
        <ManualSupplierModal open={showManualModal} onOpenChange={setShowManualModal} tenderId={tenderId} onSuccess={onRefresh} />
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-end mb-3 gap-2">
        <Button variant="outline" size="sm" onClick={() => setShowSearchModal(true)}>
          <Search className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Добавить из поиска
        </Button>
        <Button variant="outline" size="sm" onClick={() => setShowManualModal(true)}>
          <Plus className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Создать вручную
        </Button>
      </div>

      <div className="space-y-3">
        {lotSuppliers.map((ls) => (
          <div key={ls.id} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <Building2 className="h-5 w-5 text-slate-500" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900 truncate">{ls.supplier_name}</p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <StatusBadge status={ls.status} size="sm" />
                    {ls.has_cp && <span className="text-xs text-green-600 font-medium">КП: {ls.cp_margin_percent?.toFixed(1)}% маржи</span>}
                  </div>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => window.open(`/suppliers/${ls.supplier_id}`, '_blank')}>
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Dialog open={showSearchModal} onOpenChange={setShowSearchModal}>
        <DialogContent className="max-w-2xl max-h-[70vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Результаты поиска поставщиков</DialogTitle>
          </DialogHeader>
          {searchResultsQuery.isLoading ? (
            <LoadingSkeleton rows={5} cols={3} type="table" />
          ) : searchResultsQuery.isError ? (
            <ErrorAlert message="Не удалось загрузить результаты" onRetry={() => searchResultsQuery.refetch()} />
          ) : (
            <div className="space-y-2">
              {(searchResultsQuery.data?.suppliers || []).map((supplier: any) => (
                <div
                  key={supplier.id || supplier.name}
                  className={cn(
                    'flex items-center gap-3 rounded-lg border p-3',
                    selectedSuppliers[supplier.id || supplier.name] ? 'border-blue-300 bg-blue-50' : 'border-slate-200'
                  )}
                >
                  <Checkbox
                    checked={!!selectedSuppliers[supplier.id || supplier.name]}
                    onCheckedChange={(checked) =>
                      setSelectedSuppliers((prev) => ({ ...prev, [supplier.id || supplier.name]: !!checked }))
                    }
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900">{supplier.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {supplier.type && <TypeBadge type={supplier.type} size="sm" />}
                      <span className="text-xs text-slate-500">Источник: {supplier.source}</span>
                      <span className="text-xs text-slate-500">Релевантность: {supplier.relevance}</span>
                    </div>
                    {supplier.email && <p className="text-xs text-slate-500 mt-0.5">{supplier.email}</p>}
                  </div>
                  {supplier.already_in_db ? <span className="text-xs text-green-600">В базе</span> : <span className="text-xs text-blue-600">Новый</span>}
                </div>
              ))}
              {(!searchResultsQuery.data?.suppliers || searchResultsQuery.data.suppliers.length === 0) && (
                <EmptyState title="Поиск не выполнялся" description="Запустите поиск поставщиков" />
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSearchModal(false)}>
              Отмена
            </Button>
            <Button onClick={handleConfirmSuppliers}>
              Подтвердить выбранных ({Object.values(selectedSuppliers).filter(Boolean).length})
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ManualSupplierModal open={showManualModal} onOpenChange={setShowManualModal} tenderId={tenderId} onSuccess={onRefresh} />
    </div>
  );
}

function ManualSupplierModal({
  open,
  onOpenChange,
  tenderId,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenderId: string;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    name: '',
    email: '',
    phone: '',
    website: '',
    type: 'unknown',
    tags: '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      toast.error('Название обязательно');
      return;
    }
    setIsLoading(true);
    try {
      const supplier = await suppliersApi.create({
        name: form.name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        website: form.website.trim(),
        type: form.type,
        tags: form.tags ? form.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
      });
      await tendersApi.confirmSuppliers(tenderId, { supplier_ids: [supplier.id] });
      toast.success('Поставщик создан и привязан');
      onSuccess();
      onOpenChange(false);
    } catch {
      toast.error('Не удалось создать поставщика');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Новый поставщик</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Название *</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="ООО «Компания»" />
          </div>
          <div>
            <Label>Email</Label>
            <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="sales@company.ru" />
          </div>
          <div>
            <Label>Телефон</Label>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+7 (900) 000-00-00" />
          </div>
          <div>
            <Label>Сайт</Label>
            <Input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} placeholder="https://company.ru" />
          </div>
          <div>
            <Label>Тип</Label>
            <Select value={form.type} onValueChange={(value) => setForm({ ...form, type: value })}>
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unknown">Неизвестно</SelectItem>
                <SelectItem value="manufacturer">Производитель</SelectItem>
                <SelectItem value="distributor">Дистрибьютор</SelectItem>
                <SelectItem value="wholesaler">Оптовик</SelectItem>
                <SelectItem value="retail">Розница</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Теги (через запятую)</Label>
            <Input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="оргтехника, ноутбуки" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Отмена
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Создание...' : 'Создать и привязать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================
// Вкладка «Переписка»
// ============================================================
function TenderCommunicationsTab({ tenderId }: { tenderId: string }) {
  const [composerOpen, setComposerOpen] = useState(false);
  const [composerForm, setComposerForm] = useState({
    supplier_id: '',
    channel: 'email',
    subject: '',
    body: '',
  });

  const communicationsQuery = useQuery({
    queryKey: ['tender', tenderId, 'communications'],
    queryFn: () => tendersApi.getCommunications(tenderId),
  });

  const handleSend = async () => {
    if (!composerForm.supplier_id || !composerForm.subject.trim() || !composerForm.body.trim()) {
      toast.error('Заполните все поля');
      return;
    }
    try {
      await tendersApi.sendCommunication(tenderId, {
        supplier_id: composerForm.supplier_id,
        channel: composerForm.channel,
        subject: composerForm.subject,
        body: composerForm.body,
        message_type: 'manual',
      });
      toast.success('Сообщение отправлено');
      setComposerOpen(false);
      setComposerForm({ supplier_id: '', channel: 'email', subject: '', body: '' });
      communicationsQuery.refetch();
    } catch {
      toast.error('Не удалось отправить сообщение');
    }
  };

  if (communicationsQuery.isLoading) return <LoadingSkeleton rows={5} cols={1} type="card" />;
  if (communicationsQuery.isError) return <ErrorAlert message="Не удалось загрузить переписку" onRetry={() => communicationsQuery.refetch()} />;

  const threads = communicationsQuery.data?.supplier_threads || [];
  if (threads.length === 0) return <EmptyState icon={FileText} title="Переписки нет" description="Запросите КП у поставщиков" />;

  return (
    <div className="space-y-6">
      {threads.map((thread: any) => (
        <div key={thread.lot_supplier_id} className="rounded-lg border border-slate-200 bg-white">
          <div className="flex items-center justify-between p-4 border-b border-slate-200">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-900">{thread.supplier_name}</span>
              <span className="text-xs text-slate-500">({thread.status})</span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setComposerForm((prev) => ({ ...prev, supplier_id: thread.supplier_id }));
                setComposerOpen(true);
              }}
            >
              <Send className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Написать
            </Button>
          </div>
          <div className="divide-y divide-slate-100">
            {thread.messages?.map((message: any) => (
              <div key={message.id} className={cn('p-4', message.direction === 'outgoing' ? 'bg-blue-50/30' : 'bg-white')}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-slate-500">
                    {message.direction === 'outgoing' ? 'Мы →' : `${thread.supplier_name} →`}
                  </span>
                  <span className="text-xs text-slate-400">{formatDateTime(message.sent_at || message.received_at)}</span>
                  <span className="text-xs text-slate-400">({message.channel})</span>
                </div>
                <p className="text-sm font-medium text-slate-900 mb-1">{message.subject}</p>
                <p className="text-sm text-slate-700 whitespace-pre-wrap">{message.body_text}</p>
              </div>
            ))}
          </div>
        </div>
      ))}

      <Dialog open={composerOpen} onOpenChange={setComposerOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Новое сообщение</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Поставщик</Label>
              <Select value={composerForm.supplier_id} onValueChange={(value) => setComposerForm({ ...composerForm, supplier_id: value })}>
                <SelectTrigger className="mt-1"><SelectValue placeholder="Выберите поставщика" /></SelectTrigger>
                <SelectContent>
                  {threads.map((t: any) => <SelectItem key={t.supplier_id} value={t.supplier_id}>{t.supplier_name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Канал</Label>
              <Select value={composerForm.channel} onValueChange={(value) => setComposerForm({ ...composerForm, channel: value })}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="telegram">Telegram</SelectItem>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Тема</Label>
              <Input value={composerForm.subject} onChange={(e) => setComposerForm({ ...composerForm, subject: e.target.value })} placeholder="Тема сообщения" className="mt-1" />
            </div>
            <div>
              <Label>Текст</Label>
              <Textarea
                value={composerForm.body}
                onChange={(e) => setComposerForm({ ...composerForm, body: e.target.value })}
                rows={4}
                placeholder="Текст сообщения..."
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setComposerOpen(false)}>Отмена</Button>
            <Button onClick={handleSend}><Send className="h-4 w-4 mr-2" aria-hidden="true" />Отправить</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// ============================================================
// Вкладка «КП»
// ============================================================
function TenderOffersTab({
  tenderId,
  onNavigateToNegotiation,
}: {
  tenderId: string;
  onNavigateToNegotiation: (action: 'request_clarification' | 'request_discount' | 'request_both') => void;
}) {
  const [expandedOffers, setExpandedOffers] = useState<Record<string, boolean>>({});
  const offersQuery = useQuery({
    queryKey: ['tender', tenderId, 'offers'],
    queryFn: () => commercialOffersApi.list({ tender_id: tenderId }),
  });

  if (offersQuery.isLoading) return <LoadingSkeleton rows={3} cols={1} type="card" />;
  if (offersQuery.isError) return <ErrorAlert message="Не удалось загрузить КП" onRetry={() => offersQuery.refetch()} />;

  const offers = offersQuery.data || [];
  if (offers.length === 0) return <EmptyState icon={FileText} title="КП не получены" description="Запросите КП у поставщиков" />;

  return (
    <div className="space-y-3">
      {offers.map((offer: any) => {
        const isExpanded = expandedOffers[offer.id];
        return (
          <div key={offer.id} className="rounded-lg border border-slate-200 bg-white">
            <button
              className="w-full flex items-center justify-between p-4 hover:bg-slate-50"
              onClick={() => setExpandedOffers((prev) => ({ ...prev, [offer.id]: !prev[offer.id] }))}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText className="h-5 w-5 text-slate-500" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900">КП от {offer.supplier_name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-500">Покрытие: <span className="font-medium">{offer.coverage}%</span></span>
                    <span className="text-xs text-slate-500">Маржа: <span className="font-semibold text-green-600">{offer.margin_percent?.toFixed(1)}%</span></span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <StatusBadge status={offer.status} size="sm" />
                {isExpanded ? (
                  <ChevronUp className="h-4 w-4 text-slate-400" aria-hidden="true" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-slate-400" aria-hidden="true" />
                )}
              </div>
            </button>
            {isExpanded && (
              <div className="border-t border-slate-200 p-4 space-y-4">
                {offer.positions?.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-slate-900 mb-2">Позиции</h4>
                    <div className="rounded-md border border-slate-200 overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-slate-50 text-xs text-slate-500 uppercase">
                            <th className="px-3 py-2 text-left">Наименование</th>
                            <th className="px-3 py-2 text-right">Цена</th>
                            <th className="px-3 py-2 text-center">Статус</th>
                            <th className="px-3 py-2 text-right">Доставка</th>
                          </tr>
                        </thead>
                        <tbody>
                          {offer.positions.map((pos: any) => (
                            <tr key={pos.id} className="border-t border-slate-100">
                              <td className="px-3 py-2 text-slate-900">{pos.supplier_name}</td>
                              <td className="px-3 py-2 text-right text-slate-900">{formatMoney(pos.price_per_unit)}</td>
                              <td className="px-3 py-2 text-center">
                                {pos.match_type === 'exact' ? (
                                  <span className="text-green-600 text-xs">✓ exact</span>
                                ) : pos.match_type === 'analog' ? (
                                  <span className="text-yellow-600 text-xs">~ analog</span>
                                ) : (
                                  <span className="text-red-600 text-xs">✗ нет</span>
                                )}
                              </td>
                              <td className="px-3 py-2 text-right text-slate-600">
                                {pos.delivery_days ? `${pos.delivery_days} дн.` : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
                {offer.calculated && (
                  <div className="rounded-md bg-slate-50 p-3 space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Позиции:</span>
                      <span className="font-medium">{formatMoney(offer.calculated.total_positions_cost)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-500">Доставка:</span>
                      <span className="font-medium">{formatMoney(offer.calculated.delivery_cost)}</span>
                    </div>
                    <div className="flex justify-between text-sm border-t border-slate-200 pt-2">
                      <span className="font-semibold text-slate-900">ИТОГО:</span>
                      <span className="font-semibold text-slate-900">{formatMoney(offer.calculated.total_cost_with_all)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="font-semibold text-green-700">МАРЖА:</span>
                      <span className="font-semibold text-green-700">
                        {formatMoney(offer.calculated.margin_absolute)} ({offer.calculated.margin_percent?.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                )}
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => commercialOffersApi.reparse(offer.id).then(() => toast.success('Перепарсинг запущен')).catch(() => toast.error('Ошибка'))}
                  >
                    <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Перепарсить
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => onNavigateToNegotiation('request_clarification')}>
                    <Send className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Уточнить
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => onNavigateToNegotiation('request_discount')}>
                    <Wallet className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Скидка
                  </Button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// Вкладка «Переговоры»
// ============================================================
function TenderNegotiationTab({
  tenderId,
  tenderStatus,
  onRefresh,
  initialAction = null,
}: {
  tenderId: string;
  tenderStatus: string;
  onRefresh: () => void;
  initialAction?: 'request_clarification' | 'request_discount' | 'request_both' | null;
}) {
  const [currentAction, setCurrentAction] = useState<'request_clarification' | 'request_discount' | 'request_both' | null>(initialAction);

  useEffect(() => {
    setCurrentAction(initialAction);
  }, [initialAction]);

  const negotiationQuery = useQuery({
    queryKey: ['tender', tenderId, 'negotiation'],
    queryFn: () => tendersApi.getNegotiationStatus(tenderId),
    enabled: ['NEGOTIATING', 'READY_FOR_DECISION', 'CP_FULLY_RECEIVED', 'CP_PARTIALLY_RECEIVED'].includes(tenderStatus),
  });

  const handleStartNegotiation = async (action: string) => {
    try {
      await tendersApi.negotiate(tenderId, { action, target_supplier_ids: [] });
      toast.success('Переговоры запущены');
      setCurrentAction(action as 'request_clarification' | 'request_discount' | 'request_both');
      onRefresh();
      negotiationQuery.refetch();
    } catch {
      toast.error('Не удалось запустить переговоры');
    }
  };

  if (!['NEGOTIATING', 'READY_FOR_DECISION', 'CP_FULLY_RECEIVED', 'CP_PARTIALLY_RECEIVED'].includes(tenderStatus)) {
    return <EmptyState icon={MessagesSquare} title="Переговоры ещё не начаты" description="Дождитесь получения КП от поставщиков" />;
  }

  if (negotiationQuery.isLoading) return <LoadingSkeleton rows={3} cols={1} type="card" />;
  if (negotiationQuery.isError) return <ErrorAlert message="Не удалось загрузить статус переговоров" onRetry={() => negotiationQuery.refetch()} />;

  const negotiation = negotiationQuery.data;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MessagesSquare className="h-5 w-5 text-slate-500" aria-hidden="true" />
            <div>
              <p className="text-sm font-semibold text-slate-900">
                Статус: <StatusBadge status={negotiation?.status || 'UNKNOWN'} size="sm" />
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Цикл: {negotiation?.cycles_completed || 0} из {negotiation?.max_cycles || '?'}
                {negotiation?.started_at && ` | Начаты: ${formatDateTime(negotiation.started_at)}`}
              </p>
            </div>
          </div>
        </div>
      </div>

      {negotiation?.suppliers?.length > 0 && (
        <div className="rounded-lg border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Поставщик</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Нач. маржа</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Тек. маржа</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Улучшение</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Статус</th>
              </tr>
            </thead>
            <tbody>
              {negotiation.suppliers.map((supplier: any) => (
                <tr key={supplier.supplier_id} className="border-b border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-900">{supplier.supplier_name}</td>
                  <td className="px-4 py-3 text-right text-slate-600">
                    {supplier.initial_margin_percent ? `${supplier.initial_margin_percent.toFixed(1)}%` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-green-600">
                    {supplier.current_margin_percent ? `${supplier.current_margin_percent.toFixed(1)}%` : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {supplier.improvement_percent ? (
                      <span className="text-green-600 font-medium">+{supplier.improvement_percent.toFixed(1)}%</span>
                    ) : (
                      <span className="text-slate-400">0%</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center"><StatusBadge status={supplier.status} size="sm" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          className={cn(currentAction === 'request_clarification' && 'border-blue-500 text-blue-700')}
          onClick={() => handleStartNegotiation('request_clarification')}
        >
          <Send className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Запустить уточнения
        </Button>
        <Button
          variant="outline"
          size="sm"
          className={cn(currentAction === 'request_discount' && 'border-blue-500 text-blue-700')}
          onClick={() => handleStartNegotiation('request_discount')}
        >
          <Wallet className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Запустить скидки
        </Button>
        <Button
          variant="outline"
          size="sm"
          className={cn(currentAction === 'request_both' && 'border-blue-500 text-blue-700')}
          onClick={() => handleStartNegotiation('request_both')}
        >
          <Play className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Оба действия
        </Button>
      </div>
    </div>
  );
}

// ============================================================
// Вкладка «Хронология»
// ============================================================
const EVENT_ICONS: Record<string, { icon: LucideIcon; color: string }> = {
  STATUS_CHANGE: { icon: Circle, color: 'text-blue-500 bg-blue-100' },
  SUPPLIER_ADDED: { icon: UserPlus, color: 'text-purple-500 bg-purple-100' },
  CP_RECEIVED: { icon: Inbox, color: 'text-green-500 bg-green-100' },
  NEGOTIATION_STEP: { icon: MessagesSquare, color: 'text-yellow-500 bg-yellow-100' },
  DECISION: { icon: CheckCircle2, color: 'text-green-600 bg-green-100' },
  ERROR: { icon: AlertCircle, color: 'text-red-500 bg-red-100' },
};

function TenderTimelineTab({ tenderId }: { tenderId: string }) {
  const timelineQuery = useQuery({
    queryKey: ['tender', tenderId, 'timeline'],
    queryFn: () => tendersApi.timeline(tenderId),
  });

  if (timelineQuery.isLoading) return <LoadingSkeleton rows={5} cols={1} type="card" />;
  if (timelineQuery.isError) return <ErrorAlert message="Не удалось загрузить хронологию" onRetry={() => timelineQuery.refetch()} />;

  const events = timelineQuery.data || [];
  if (events.length === 0) return <EmptyState title="Событий нет" description="Хронология будет заполняться по мере обработки тендера" />;

  return (
    <div className="relative pl-8">
      <div className="absolute left-3 top-2 bottom-2 w-px bg-slate-200" />
      <div className="space-y-6">
        {events.map((event: TenderTimelineEvent, index: number) => {
          const config = EVENT_ICONS[event.event_type] || EVENT_ICONS.STATUS_CHANGE;
          const Icon = config.icon;
          return (
            <div key={index} className="relative">
              <div className={cn('absolute -left-8 top-1 w-5 h-5 rounded-full flex items-center justify-center', config.color)}>
                <Icon className="w-3 h-3" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">{event.description}</p>
                <p className="text-xs text-slate-400 mt-0.5">{formatDateTime(event.timestamp)}</p>
                {event.details && Object.keys(event.details).length > 0 && (
                  <p className="text-xs text-slate-500 mt-1">
                    {Object.entries(event.details).map(([key, value]) => `${key}: ${value}`).join(' | ')}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================
// Кнопки действий
// ============================================================
function ActionButtons({
  tender,
  onPatchStatus,
  onReprocess,
  onNavigateToTab,
  onNavigateDecisions,
}: {
  tender: TenderDetail;
  onPatchStatus: (status: string, note: string) => void;
  onReprocess: (fromStage: string) => void;
  onNavigateToTab: (tab: string) => void;
  onNavigateDecisions: () => void;
}) {
  const [showRequestCP, setShowRequestCP] = useState(false);
  const [attachTable, setAttachTable] = useState(true);
  const status = tender.status;

  const handleRequestCP = async () => {
    try {
      await tendersApi.requestCP(tender.id, { attach_positions_table: attachTable });
      toast.success('Запрос КП отправлен');
      setShowRequestCP(false);
    } catch {
      toast.error('Не удалось запросить КП');
    }
  };

  if (status === 'NEW') {
    return <Button onClick={() => onReprocess('DOCUMENTS_LOADING')}><Play className="h-4 w-4 mr-2" aria-hidden="true" />Запустить обработку</Button>;
  }
  if (['DOCUMENTS_LOADING', 'PROCESSING', 'SEMANTIC_FILTERING', 'SCORING', 'SUPPLIER_SEARCH_IN_PROGRESS', 'CP_REQUESTED', 'NEGOTIATING'].includes(status)) {
    return <Button disabled><Loader2 className="h-4 w-4 mr-2 animate-spin" aria-hidden="true" />Обработка...</Button>;
  }
  if (status === 'DOCUMENTS_LOADED') {
    return <Button onClick={() => onReprocess('SEMANTIC_FILTERING')}><Play className="h-4 w-4 mr-2" aria-hidden="true" />Запустить фильтрацию</Button>;
  }
  if (status === 'UNCERTAIN') {
    return (
      <div className="flex gap-2">
        <Button onClick={() => onPatchStatus('RELEVANT', 'Подтверждено вручную')}>
          <CheckCircle2 className="h-4 w-4 mr-2" aria-hidden="true" />Подтвердить
        </Button>
        <Button variant="outline" onClick={() => onPatchStatus('NOT_RELEVANT', 'Отклонено вручную')}>
          <XCircle className="h-4 w-4 mr-2" aria-hidden="true" />Отклонить
        </Button>
      </div>
    );
  }
  if (status === 'RELEVANT') {
    return <Button onClick={() => onReprocess('SCORING')}><Play className="h-4 w-4 mr-2" aria-hidden="true" />Запустить скоринг</Button>;
  }
  if (status === 'SCORED') {
    return <Button onClick={() => onNavigateToTab('suppliers')}><Search className="h-4 w-4 mr-2" aria-hidden="true" />Найти поставщиков</Button>;
  }
  if (status === 'SUPPLIERS_FOUND') {
    return <Button onClick={() => onNavigateToTab('suppliers')}><Users className="h-4 w-4 mr-2" aria-hidden="true" />Подтвердить поставщиков</Button>;
  }
  if (status === 'AWAITING_CP') {
    return (
      <>
        <Button onClick={() => setShowRequestCP(true)}><Send className="h-4 w-4 mr-2" aria-hidden="true" />Запросить КП</Button>
        <Dialog open={showRequestCP} onOpenChange={setShowRequestCP}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Запрос коммерческих предложений</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <label className="flex items-center gap-2 text-sm">
                <Checkbox checked={attachTable} onCheckedChange={(checked) => setAttachTable(!!checked)} />
                Прикрепить таблицу позиций (Excel)
              </label>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowRequestCP(false)}>Отмена</Button>
              <Button onClick={handleRequestCP}>Отправить запросы</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </>
    );
  }
  if (status === 'CP_FULLY_RECEIVED') {
    return <Button onClick={() => onNavigateToTab('negotiation')}><MessagesSquare className="h-4 w-4 mr-2" aria-hidden="true" />Начать переговоры</Button>;
  }
  if (status === 'READY_FOR_DECISION') {
    return <Button onClick={onNavigateDecisions}><ClipboardCheck className="h-4 w-4 mr-2" aria-hidden="true" />Перейти к решению</Button>;
  }
  if (status === 'ERROR') {
    return <Button onClick={() => onReprocess('DOCUMENTS_LOADING')}><RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />Повторить обработку</Button>;
  }
  return null;
}

// ============================================================
// Главный компонент страницы
// ============================================================
export function TenderDetailPage() {
  const { tenderId } = useParams<{ tenderId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [negotiationAction, setNegotiationAction] = useState<'request_clarification' | 'request_discount' | 'request_both' | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    title: string;
    description: string;
    confirmLabel: string;
    variant: 'default' | 'destructive';
    onConfirm: () => void;
  }>({ open: false, title: '', description: '', confirmLabel: 'Подтвердить', variant: 'default', onConfirm: () => {} });

  const tenderQuery = useQuery({
    queryKey: ['tender', tenderId],
    queryFn: () => tendersApi.get(tenderId!),
    enabled: !!tenderId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return ['PROCESSING', 'SCORING', 'SUPPLIER_SEARCH_IN_PROGRESS', 'CP_REQUESTED', 'NEGOTIATING'].includes(status) ? 10_000 : false;
    },
  });

  const handlePatchStatus = async (status: string, note: string) => {
    try {
      await tendersApi.patch(tenderId!, { status, note });
      toast.success('Статус обновлён');
      tenderQuery.refetch();
    } catch {
      toast.error('Не удалось обновить статус');
    }
  };

  const handleReprocess = async (fromStage: string) => {
    try {
      await tendersApi.reprocess(tenderId!, { from_stage: fromStage });
      toast.success('Обработка запущена');
      tenderQuery.refetch();
    } catch {
      toast.error('Не удалось запустить обработку');
    }
  };

  const confirmAction = (description: string, onConfirm: () => void, variant: 'default' | 'destructive' = 'default') => {
    setConfirmDialog({
      open: true,
      title: 'Подтверждение',
      description,
      confirmLabel: 'Подтвердить',
      variant,
      onConfirm: () => {
        onConfirm();
        setConfirmDialog((prev) => ({ ...prev, open: false }));
      },
    });
  };

  if (tenderQuery.isLoading) {
    return <LoadingSkeleton rows={3} cols={3} type="card" />;
  }
  if (tenderQuery.isError) {
    return <ErrorAlert message="Не удалось загрузить тендер" onRetry={() => tenderQuery.refetch()} />;
  }

  const tender = tenderQuery.data;
  if (!tender) return null;

  const positions = tender.structured_data?.positions || [];
  const documents = tender.documents || [];
  const suppliers = tender.suppliers || [];

  return (
    <div>
      <button
        onClick={() => navigate('/tenders')}
        className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-3"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Назад к тендерам
      </button>

      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-semibold text-slate-900 truncate">{tender.title}</h1>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <StatusBadge status={tender.status} />
            <ScoreBadge score={tender.score} />
            <span className="text-sm text-slate-600">НМЦК: <span className="font-medium">{formatMoney(tender.nmck)}</span></span>
            <span className="text-sm text-slate-600">Дедлайн: <span className="font-medium">{formatDate(tender.deadline_at)}</span></span>
            {tender.matched_category_name && (
              <span className="text-sm text-slate-600">Категория: <span className="font-medium">{tender.matched_category_name}</span></span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ActionButtons
            tender={tender}
            onPatchStatus={(status, note) => confirmAction('Изменить статус?', () => handlePatchStatus(status, note))}
            onReprocess={handleReprocess}
            onNavigateToTab={(tab) => setActiveTab(tab)}
            onNavigateDecisions={() => navigate('/decisions')}
          />
          <Button variant="outline" size="sm" onClick={() => tenderQuery.refetch()}>
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
            Обновить
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
        <TabsList className="border-b border-slate-200 w-full justify-start gap-1 rounded-none bg-transparent p-0">
          <TabsTrigger value="overview" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Обзор
          </TabsTrigger>
          <TabsTrigger value="positions" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Позиции ({positions.length})
          </TabsTrigger>
          <TabsTrigger value="documents" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Документы ({documents.length})
          </TabsTrigger>
          <TabsTrigger value="suppliers" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Поставщики ({suppliers.length})
          </TabsTrigger>
          <TabsTrigger value="communications" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Переписка
          </TabsTrigger>
          <TabsTrigger value="offers" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            КП
          </TabsTrigger>
          <TabsTrigger value="negotiation" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Переговоры
          </TabsTrigger>
          <TabsTrigger value="timeline" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Хронология
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4"><TenderOverviewTab tender={tender} /></TabsContent>
        <TabsContent value="positions" className="mt-4"><TenderPositionsTab positions={positions} /></TabsContent>
        <TabsContent value="documents" className="mt-4"><TenderDocumentsTab documents={documents} /></TabsContent>
        <TabsContent value="suppliers" className="mt-4">
          <TenderSuppliersTab tenderId={tenderId!} lotSuppliers={suppliers} onRefresh={() => tenderQuery.refetch()} />
        </TabsContent>
        <TabsContent value="communications" className="mt-4">
          <TenderCommunicationsTab tenderId={tenderId!} />
        </TabsContent>
        <TabsContent value="offers" className="mt-4">
          <TenderOffersTab
            tenderId={tenderId!}
            onNavigateToNegotiation={(action) => {
              setNegotiationAction(action);
              setActiveTab('negotiation');
            }}
          />
        </TabsContent>
        <TabsContent value="negotiation" className="mt-4">
          <TenderNegotiationTab
            tenderId={tenderId!}
            tenderStatus={tender.status}
            onRefresh={() => tenderQuery.refetch()}
            initialAction={negotiationAction}
          />
        </TabsContent>
        <TabsContent value="timeline" className="mt-4"><TenderTimelineTab tenderId={tenderId!} /></TabsContent>
      </Tabs>

      <ConfirmDialog
        open={confirmDialog.open}
        onOpenChange={(open) => setConfirmDialog((prev) => ({ ...prev, open }))}
        title={confirmDialog.title}
        description={confirmDialog.description}
        confirmLabel={confirmDialog.confirmLabel}
        variant={confirmDialog.variant}
        onConfirm={confirmDialog.onConfirm}
      />
    </div>
  );
}