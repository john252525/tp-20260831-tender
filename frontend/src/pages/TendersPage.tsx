import { useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useDebounce } from '../hooks/useDebounce';
import {
  Search,
  MoreHorizontal,
  RefreshCw,
  FileText,
  X,
  Play,
  Users,
  Send,
  MessagesSquare,
  Download,
  CheckCircle2,
  XCircle,
  ClipboardCheck,
} from 'lucide-react';
import { toast } from 'sonner';
import { tendersApi, type TenderListItem } from '../api/tenders';
import { categoriesApi } from '../api/categories';
import { tenderSourcesApi } from '../api/tenderSources';
import { StatusBadge } from '../components/common/StatusBadge';
import { ScoreBadge } from '../components/common/ScoreBadge';
import { DataTable } from '../components/common/DataTable';
import { EmptyState } from '../components/common/EmptyState';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
import { formatMoney, formatDate } from '../lib/formatters';
import { cn } from '../lib/utils';
import type { ColumnDef, SortingState, RowSelectionState } from '@tanstack/react-table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Checkbox } from '../components/ui/checkbox';

// ============================================================
// Типы фильтров
// ============================================================
interface TenderFilters {
  search: string;
  status: string[];
  category_id: string | null;
  source_id: string | null;
  nmck_min: string;
  nmck_max: string;
  published_after: string;
  published_before: string;
  deadline_after: string;
  deadline_before: string;
  has_score: boolean;
  score_min: string;
  score_max: string;
  sort_by: string;
  sort_order: 'asc' | 'desc';
  page: number;
  per_page: number;
}

const SORT_OPTIONS = [
  { value: 'created_at', label: 'По дате создания' },
  { value: 'published_at', label: 'По дате публикации' },
  { value: 'nmck', label: 'По НМЦК' },
  { value: 'deadline_at', label: 'По дедлайну' },
  { value: 'score', label: 'По скору' },
  { value: 'status', label: 'По статусу' },
];

const STATUS_OPTIONS = [
  'NEW', 'DOCUMENTS_LOADING', 'DOCUMENTS_LOADED', 'PROCESSING',
  'SEMANTIC_FILTERING', 'RELEVANT', 'UNCERTAIN', 'NOT_RELEVANT',
  'SCORING', 'SCORED', 'AWAITING_SUPPLIER_SEARCH',
  'SUPPLIER_SEARCH_IN_PROGRESS', 'SUPPLIERS_FOUND', 'NO_SUPPLIERS_FOUND',
  'AWAITING_CP', 'CP_REQUESTED', 'CP_PARTIALLY_RECEIVED',
  'CP_FULLY_RECEIVED', 'NEGOTIATING', 'READY_FOR_DECISION',
  'APPROVED', 'REJECTED', 'ERROR',
];

// ============================================================
// Модалки
// ============================================================
function ReprocessModal({ open, onOpenChange, selectedCount, onConfirm, isLoading }: {
  open: boolean; onOpenChange: (open: boolean) => void; selectedCount: number; onConfirm: (fromStage: string) => void; isLoading: boolean;
}) {
  const [fromStage, setFromStage] = useState('DOCUMENTS_LOADING');
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Обработать тендеры</DialogTitle>
          <DialogDescription>Выбрано: {selectedCount} тендер(ов). Выберите этап для перезапуска.</DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label>Этап перезапуска</Label>
          <select value={fromStage} onChange={(e) => setFromStage(e.target.value)} className="w-full h-9 border border-slate-200 rounded-md px-3 text-sm">
            <option value="DOCUMENTS_LOADING">Загрузка документов</option>
            <option value="SEMANTIC_FILTERING">Семантическая фильтрация</option>
            <option value="SCORING">Скоринг</option>
            <option value="SUPPLIER_SEARCH">Поиск поставщиков</option>
          </select>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={() => onConfirm(fromStage)} disabled={isLoading}>
            {isLoading ? 'Запуск...' : `Запустить (${selectedCount})`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SearchSuppliersModal({ open, onOpenChange, selectedCount, onConfirm, isLoading }: {
  open: boolean; onOpenChange: (open: boolean) => void; selectedCount: number; onConfirm: (data: any) => void; isLoading: boolean;
}) {
  const [maxSuppliers, setMaxSuppliers] = useState(10);
  const [channels, setChannels] = useState(['google', 'internal_db']);
  const [priority, setPriority] = useState(['manufacturer', 'distributor', 'wholesaler']);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Поиск поставщиков</DialogTitle><DialogDescription>Выбрано: {selectedCount} тендер(ов)</DialogDescription></DialogHeader>
        <div className="space-y-4">
          <div><Label>Максимум поставщиков на лот</Label><Input type="number" value={maxSuppliers} onChange={(e) => setMaxSuppliers(Number(e.target.value))} min={1} max={50} className="mt-1" /></div>
          <div>
            <Label>Каналы поиска</Label>
            <div className="flex gap-4 mt-2">
              <label className="flex items-center gap-2 text-sm"><Checkbox checked={channels.includes('google')} onCheckedChange={(checked) => setChannels(checked ? [...channels, 'google'] : channels.filter((c) => c !== 'google'))} />Google Search</label>
              <label className="flex items-center gap-2 text-sm"><Checkbox checked={channels.includes('internal_db')} onCheckedChange={(checked) => setChannels(checked ? [...channels, 'internal_db'] : channels.filter((c) => c !== 'internal_db'))} />Внутренняя база</label>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={() => onConfirm({ max_suppliers: maxSuppliers, channels, priority_order: priority })} disabled={isLoading}>{isLoading ? 'Запуск...' : 'Начать поиск'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RequestCPModal({ open, onOpenChange, selectedCount, onConfirm, isLoading }: {
  open: boolean; onOpenChange: (open: boolean) => void; selectedCount: number; onConfirm: (data: any) => void; isLoading: boolean;
}) {
  const [attachTable, setAttachTable] = useState(true);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Запрос коммерческих предложений</DialogTitle><DialogDescription>Выбрано: {selectedCount} тендер(ов)</DialogDescription></DialogHeader>
        <div className="space-y-4">
          <label className="flex items-center gap-2 text-sm"><Checkbox checked={attachTable} onCheckedChange={(checked) => setAttachTable(!!checked)} />Прикрепить таблицу позиций (Excel)</label>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={() => onConfirm({ attach_positions_table: attachTable })} disabled={isLoading}>{isLoading ? 'Отправка...' : 'Отправить запросы'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function NegotiateModal({ open, onOpenChange, selectedCount, onConfirm, isLoading }: {
  open: boolean; onOpenChange: (open: boolean) => void; selectedCount: number; onConfirm: (data: any) => void; isLoading: boolean;
}) {
  const [action, setAction] = useState('request_clarification');
  const [instructions, setInstructions] = useState('');
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Переговоры</DialogTitle><DialogDescription>Выбрано: {selectedCount} тендер(ов)</DialogDescription></DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Действие</Label>
            <div className="space-y-2 mt-2">
              <label className="flex items-center gap-2 text-sm"><input type="radio" checked={action === 'request_clarification'} onChange={() => setAction('request_clarification')} />Уточнение недостающей информации</label>
              <label className="flex items-center gap-2 text-sm"><input type="radio" checked={action === 'request_discount'} onChange={() => setAction('request_discount')} />Запрос скидки</label>
              <label className="flex items-center gap-2 text-sm"><input type="radio" checked={action === 'request_both'} onChange={() => setAction('request_both')} />Оба действия</label>
            </div>
          </div>
          <div><Label>Дополнительная инструкция (опционально)</Label><textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} className="w-full h-20 border border-slate-200 rounded-md px-3 py-2 text-sm mt-1" placeholder="Например: уточните сроки доставки" /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={() => onConfirm({ action, custom_instructions: instructions || undefined })} disabled={isLoading}>{isLoading ? 'Запуск...' : 'Начать'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ============================================================
// Главный компонент страницы
// ============================================================
export function TendersPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(() => searchParams.get('search') || '');
  const debouncedSearch = useDebounce(searchInput, 300);

  const filters: TenderFilters = useMemo(() => {
    return {
      search: debouncedSearch,
      status: searchParams.get('status') ? searchParams.get('status')!.split(',') : [],
      category_id: searchParams.get('category_id'),
      source_id: searchParams.get('source_id'),
      nmck_min: searchParams.get('nmck_min') || '',
      nmck_max: searchParams.get('nmck_max') || '',
      published_after: searchParams.get('published_after') || '',
      published_before: searchParams.get('published_before') || '',
      deadline_after: searchParams.get('deadline_after') || '',
      deadline_before: searchParams.get('deadline_before') || '',
      has_score: searchParams.get('has_score') === 'true',
      score_min: searchParams.get('score_min') || '',
      score_max: searchParams.get('score_max') || '',
      sort_by: searchParams.get('sort_by') || 'created_at',
      sort_order: (searchParams.get('sort_order') as 'asc' | 'desc') || 'desc',
      page: Number(searchParams.get('page') || 1),
      per_page: Number(searchParams.get('per_page') || 20),
    };
  }, [searchParams, debouncedSearch]);

  useEffect(() => {
    const newParams = new URLSearchParams(searchParams);
    const currentSearch = searchParams.get('search') || '';
    if (debouncedSearch) {
      newParams.set('search', debouncedSearch);
    } else {
      newParams.delete('search');
    }
    newParams.set('page', '1');
    if (currentSearch !== debouncedSearch || searchParams.get('page') !== '1') {
      setSearchParams(newParams, { replace: true });
    }
  }, [debouncedSearch]); // eslint-disable-line react-hooks/exhaustive-deps

  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [sorting, setSorting] = useState<SortingState>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [modalState, setModalState] = useState<'none' | 'reprocess' | 'search' | 'cp' | 'negotiate'>('none');
  const [isBulkLoading, setIsBulkLoading] = useState(false);

  const tendersQuery = useQuery({
    queryKey: ['tenders', 'list', filters],
    queryFn: () => tendersApi.list({
      search: filters.search || undefined,
      status: filters.status.length > 0 ? filters.status.join(',') : undefined,
      category_id: filters.category_id || undefined,
      source_id: filters.source_id || undefined,
      nmck_min: filters.nmck_min ? Number(filters.nmck_min) : undefined,
      nmck_max: filters.nmck_max ? Number(filters.nmck_max) : undefined,
      published_after: filters.published_after || undefined,
      published_before: filters.published_before || undefined,
      deadline_after: filters.deadline_after || undefined,
      deadline_before: filters.deadline_before || undefined,
      has_score: filters.has_score || undefined,
      score_min: filters.score_min ? Number(filters.score_min) : undefined,
      score_max: filters.score_max ? Number(filters.score_max) : undefined,
      sort_by: filters.sort_by,
      sort_order: filters.sort_order,
      page: filters.page,
      per_page: filters.per_page,
    }),
  });

  const categoriesQuery = useQuery({ queryKey: ['categories', 'all'], queryFn: () => categoriesApi.list({ per_page: 100 }) });
  const sourcesQuery = useQuery({ queryKey: ['tender-sources', 'all'], queryFn: () => tenderSourcesApi.list() });

  const tenders = tendersQuery.data?.data || [];
  const meta = tendersQuery.data?.meta;
  const selectedIds = Object.keys(rowSelection).filter((key) => rowSelection[key]);
  const selectedCount = selectedIds.length;

  const updateFilters = useCallback(
    (updates: Partial<TenderFilters>) => {
      const newParams = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (value === null || value === undefined || value === '' || (Array.isArray(value) && value.length === 0)) {
          newParams.delete(key);
        } else if (Array.isArray(value)) {
          newParams.set(key, value.join(','));
        } else if (typeof value === 'boolean') {
          if (value) newParams.set(key, 'true');
          else newParams.delete(key);
        } else {
          newParams.set(key, String(value));
        }
      });
      setSearchParams(newParams, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const resetFilters = () => {
    setSearchParams({}, { replace: true });
    setRowSelection({});
    setSearchInput('');
  };

  const handleBulkAction = async (action: string, data?: any) => {
    setIsBulkLoading(true);
    try {
      const ids = selectedIds;
      const promises = ids.map((id) => {
        switch (action) {
          case 'reprocess': return tendersApi.reprocess(id, { from_stage: data.from_stage });
          case 'search': return tendersApi.searchSuppliers(id, data);
          case 'cp': return tendersApi.requestCP(id, data);
          case 'negotiate': return tendersApi.negotiate(id, data);
          default: return Promise.resolve();
        }
      });
      await Promise.all(promises);
      toast.success(`Операция запущена для ${ids.length} тендер(ов)`);
      setModalState('none');
      setRowSelection({});
    } catch {
      toast.error('Не удалось выполнить операцию');
    } finally {
      setIsBulkLoading(false);
    }
  };

  const handleExportCSV = () => {
    const headers = ['ID', 'Название', 'Статус', 'НМЦК', 'Категория', 'Скор', 'Дедлайн', 'Опубликован', 'Заказчик'];
    const rows = tenders.map((t) => [t.id, t.title, t.status, t.nmck, t.matched_category_name, t.score, t.deadline_at, t.published_at, t.customer_name]);
    const csv = [headers.join(','), ...rows.map((r) => r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `tenders_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const columns: ColumnDef<TenderListItem, any>[] = useMemo(
    () => [
      {
        id: 'select',
        header: ({ table }) => (
          <Checkbox checked={table.getIsAllPageRowsSelected()} onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)} aria-label="Выбрать все" />
        ),
        cell: ({ row }) => (
          <Checkbox checked={row.getIsSelected()} onCheckedChange={(value) => row.toggleSelected(!!value)} aria-label="Выбрать строку" onClick={(e) => e.stopPropagation()} />
        ),
        size: 40,
        enableSorting: false,
      },
      {
        id: 'title',
        header: 'Название',
        accessorKey: 'title',
        cell: ({ row }) => (
          <button onClick={() => navigate(`/tenders/${row.original.id}`)} className="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline text-left truncate max-w-[300px]">
            {row.original.title}
          </button>
        ),
        size: 300,
      },
      {
        id: 'status',
        header: 'Статус',
        accessorKey: 'status',
        cell: ({ row }) => <StatusBadge status={row.original.status} size="sm" />,
        size: 130,
      },
      {
        id: 'nmck',
        header: 'НМЦК',
        accessorKey: 'nmck',
        cell: ({ row }) => <span className="text-sm text-slate-700 whitespace-nowrap">{formatMoney(row.original.nmck)}</span>,
        size: 100,
      },
      {
        id: 'category',
        header: 'Категория',
        accessorKey: 'matched_category_name',
        cell: ({ row }) => <span className="text-sm text-slate-600">{row.original.matched_category_name || '—'}</span>,
        size: 110,
        enableSorting: false,
      },
      {
        id: 'similarity',
        header: 'Сход.',
        accessorKey: 'similarity_score',
        cell: ({ row }) => <span className="text-xs text-slate-500">{row.original.similarity_score ? `${(row.original.similarity_score * 100).toFixed(0)}%` : '—'}</span>,
        size: 60,
        enableSorting: false,
      },
      {
        id: 'score',
        header: 'Скор',
        accessorKey: 'score',
        cell: ({ row }) => <ScoreBadge score={row.original.score} size="sm" />,
        size: 60,
      },
      {
        id: 'deadline',
        header: 'Дедлайн',
        accessorKey: 'deadline_at',
        cell: ({ row }) => (
          <span className={cn('text-sm', row.original.deadline_at && new Date(row.original.deadline_at) < new Date(Date.now() + 3 * 24 * 60 * 60 * 1000) ? 'text-red-600 font-medium' : 'text-slate-600')}>
            {formatDate(row.original.deadline_at)}
          </span>
        ),
        size: 90,
      },
      {
        id: 'suppliers',
        header: 'Пост.',
        accessorKey: 'suppliers_count',
        cell: ({ row }) => <span className="text-sm text-slate-600">{row.original.suppliers_count || 0}</span>,
        size: 50,
        enableSorting: false,
      },
      {
        id: 'margin',
        header: 'Маржа',
        accessorKey: 'best_margin_percent',
        cell: ({ row }) => <span className="text-sm font-medium text-green-600">{row.original.best_margin_percent ? `${row.original.best_margin_percent.toFixed(1)}%` : '—'}</span>,
        size: 60,
        enableSorting: false,
      },
      {
        id: 'actions',
        header: '',
        cell: ({ row }) => (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="p-1.5 rounded-md hover:bg-slate-100 text-slate-400" onClick={(e) => e.stopPropagation()}>
                <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => navigate(`/tenders/${row.original.id}`)}>
                <FileText className="h-4 w-4 mr-2" aria-hidden="true" />Открыть карточку
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setModalState('reprocess')}>
                <Play className="h-4 w-4 mr-2" aria-hidden="true" />Перезапустить обработку
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setModalState('search')}>
                <Users className="h-4 w-4 mr-2" aria-hidden="true" />Найти поставщиков
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setModalState('cp')}>
                <Send className="h-4 w-4 mr-2" aria-hidden="true" />Запросить КП
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setModalState('negotiate')}>
                <MessagesSquare className="h-4 w-4 mr-2" aria-hidden="true" />Переговоры
              </DropdownMenuItem>
              {row.original.status === 'UNCERTAIN' && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => { tendersApi.patch(row.original.id, { status: 'RELEVANT', note: 'Подтверждено вручную' }).then(() => { toast.success('Тендер подтверждён'); tendersQuery.refetch(); }).catch(() => toast.error('Ошибка')); }}>
                    <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" aria-hidden="true" />Подтвердить
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => { tendersApi.patch(row.original.id, { status: 'NOT_RELEVANT', note: 'Отклонено вручную' }).then(() => { toast.success('Тендер отклонён'); tendersQuery.refetch(); }).catch(() => toast.error('Ошибка')); }}>
                    <XCircle className="h-4 w-4 mr-2 text-red-600" aria-hidden="true" />Отклонить
                  </DropdownMenuItem>
                </>
              )}
              {row.original.status === 'READY_FOR_DECISION' && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate('/decisions')}>
                    <ClipboardCheck className="h-4 w-4 mr-2 text-purple-600" aria-hidden="true" />К решению
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        ),
        size: 40,
        enableSorting: false,
      },
    ],
    [navigate, tendersQuery]
  );

  return (
    <div>
      <PageHeader title="Тендеры" description={`Всего: ${meta?.total || 0}`} actions={
        <>
          <button onClick={handleExportCSV} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
            <Download className="h-4 w-4" aria-hidden="true" />Экспорт CSV
          </button>
          <button onClick={() => tendersQuery.refetch()} className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
            <RefreshCw className="h-4 w-4" aria-hidden="true" />Обновить
          </button>
          <button onClick={() => setShowFilters(!showFilters)} className={cn('inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors', showFilters ? 'border-blue-200 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50')}>
            <Search className="h-4 w-4" aria-hidden="true" />Фильтры
            {filters.status.length > 0 && <span className="bg-blue-600 text-white text-xs rounded-full px-1.5 py-0.5">{filters.status.length}</span>}
          </button>
        </>
      } />

      {showFilters && (
        <div className="rounded-lg border border-slate-200 p-4 mb-6 bg-white">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div>
              <Label className="text-xs text-slate-500">Поиск</Label>
              <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Название, описание, заказчик" className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Статус</Label>
              <select multiple value={filters.status} onChange={(e) => { const values = Array.from(e.target.selectedOptions).map((o) => o.value); updateFilters({ status: values, page: 1 }); }} className="w-full h-20 border border-slate-200 rounded-md px-2 py-1 text-sm mt-1">
                {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
              {filters.status.length > 0 && <button onClick={() => updateFilters({ status: [], page: 1 })} className="text-xs text-blue-600 mt-1">Очистить ({filters.status.length})</button>}
            </div>
            <div>
              <Label className="text-xs text-slate-500">Категория</Label>
              <select value={filters.category_id || ''} onChange={(e) => updateFilters({ category_id: e.target.value || null, page: 1 })} className="w-full h-9 border border-slate-200 rounded-md px-2 text-sm mt-1">
                <option value="">Все</option>
                {(categoriesQuery.data || []).map((cat) => <option key={cat.id} value={cat.id}>{cat.name}</option>)}
              </select>
              {categoriesQuery.isError && <p className="text-xs text-red-600 mt-1">Не удалось загрузить категории</p>}
            </div>
            <div>
              <Label className="text-xs text-slate-500">Источник</Label>
              <select value={filters.source_id || ''} onChange={(e) => updateFilters({ source_id: e.target.value || null, page: 1 })} className="w-full h-9 border border-slate-200 rounded-md px-2 text-sm mt-1">
                <option value="">Все</option>
                {(sourcesQuery.data || []).map((src) => <option key={src.id} value={src.id}>{src.name}</option>)}
              </select>
              {sourcesQuery.isError && <p className="text-xs text-red-600 mt-1">Не удалось загрузить источники</p>}
            </div>
            <div>
              <Label className="text-xs text-slate-500">НМЦК от (₽)</Label>
              <Input type="number" placeholder="0" defaultValue={filters.nmck_min} onChange={(e) => updateFilters({ nmck_min: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">НМЦК до (₽)</Label>
              <Input type="number" placeholder="∞" defaultValue={filters.nmck_max} onChange={(e) => updateFilters({ nmck_max: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Опубликован от</Label>
              <Input type="date" defaultValue={filters.published_after} onChange={(e) => updateFilters({ published_after: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Опубликован до</Label>
              <Input type="date" defaultValue={filters.published_before} onChange={(e) => updateFilters({ published_before: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Дедлайн от</Label>
              <Input type="date" defaultValue={filters.deadline_after} onChange={(e) => updateFilters({ deadline_after: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Дедлайн до</Label>
              <Input type="date" defaultValue={filters.deadline_before} onChange={(e) => updateFilters({ deadline_before: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Скор от</Label>
              <Input type="number" min={0} max={100} placeholder="0" defaultValue={filters.score_min} onChange={(e) => updateFilters({ score_min: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Скор до</Label>
              <Input type="number" min={0} max={100} placeholder="100" defaultValue={filters.score_max} onChange={(e) => updateFilters({ score_max: e.target.value, page: 1 })} className="mt-1" />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm"><Checkbox checked={filters.has_score} onCheckedChange={(checked) => updateFilters({ has_score: !!checked, page: 1 })} />Есть решение</label>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Сортировка</Label>
              <select value={filters.sort_by} onChange={(e) => updateFilters({ sort_by: e.target.value })} className="w-full h-9 border border-slate-200 rounded-md px-2 text-sm mt-1">
                {SORT_OPTIONS.map((opt) => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
              </select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Порядок</Label>
              <select value={filters.sort_order} onChange={(e) => updateFilters({ sort_order: e.target.value as 'asc' | 'desc' })} className="w-full h-9 border border-slate-200 rounded-md px-2 text-sm mt-1">
                <option value="desc">По убыванию</option>
                <option value="asc">По возрастанию</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end mt-4">
            <Button variant="outline" onClick={resetFilters}><X className="h-4 w-4 mr-2" aria-hidden="true" />Сбросить всё</Button>
          </div>
        </div>
      )}

      {selectedCount > 0 && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 mb-4 flex items-center justify-between">
          <span className="text-sm font-medium text-blue-700">Выбрано: {selectedCount} тендер(ов)</span>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setModalState('reprocess')}><Play className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Обработать</Button>
            <Button size="sm" variant="outline" onClick={() => setModalState('search')}><Users className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Поставщики</Button>
            <Button size="sm" variant="outline" onClick={() => setModalState('cp')}><Send className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Запросить КП</Button>
            <Button size="sm" variant="outline" onClick={() => setModalState('negotiate')}><MessagesSquare className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />Переговоры</Button>
            <Button size="sm" variant="ghost" onClick={() => setRowSelection({})}>Очистить</Button>
          </div>
        </div>
      )}

      {tendersQuery.isLoading ? (
        <LoadingSkeleton rows={10} cols={8} type="table" />
      ) : tendersQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить тендеры" onRetry={() => tendersQuery.refetch()} />
      ) : (
        <DataTable
          data={tenders}
          columns={columns}
          page={filters.page}
          pageCount={meta?.pages || 1}
          total={meta?.total}
          perPage={filters.per_page}
          onPageChange={(page) => updateFilters({ page })}
          onPerPageChange={(perPage) => updateFilters({ per_page: perPage, page: 1 })}
          sorting={sorting}
          onSortingChange={setSorting}
          rowSelection={rowSelection}
          onRowSelectionChange={setRowSelection}
          showCheckboxes
          onRowClick={(row) => navigate(`/tenders/${row.id}`)}
          enableVirtualization
          tableHeight={600}
          emptyState={<EmptyState icon={FileText} title="Тендеры не найдены" description="Попробуйте изменить фильтры или сбросить их" actionLabel="Сбросить фильтры" onAction={resetFilters} />}
        />
      )}

      <ReprocessModal open={modalState === 'reprocess'} onOpenChange={(open) => !open && setModalState('none')} selectedCount={selectedCount || 1} onConfirm={(fromStage) => handleBulkAction('reprocess', { from_stage: fromStage })} isLoading={isBulkLoading} />
      <SearchSuppliersModal open={modalState === 'search'} onOpenChange={(open) => !open && setModalState('none')} selectedCount={selectedCount || 1} onConfirm={(data) => handleBulkAction('search', data)} isLoading={isBulkLoading} />
      <RequestCPModal open={modalState === 'cp'} onOpenChange={(open) => !open && setModalState('none')} selectedCount={selectedCount || 1} onConfirm={(data) => handleBulkAction('cp', data)} isLoading={isBulkLoading} />
      <NegotiateModal open={modalState === 'negotiate'} onOpenChange={(open) => !open && setModalState('none')} selectedCount={selectedCount || 1} onConfirm={(data) => handleBulkAction('negotiate', data)} isLoading={isBulkLoading} />
    </div>
  );
}