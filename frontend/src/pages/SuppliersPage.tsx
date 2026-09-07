import { useState, useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Building2,
  Search,
  Plus,
  MoreHorizontal,
  RefreshCw,
  Pencil,
  Trash2,
  GitMerge,
  ExternalLink,
} from 'lucide-react';
import { suppliersApi, type SupplierListItem } from '../api/suppliers';
import { TypeBadge } from '../components/common/TypeBadge';
import { TagChip } from '../components/common/TagChip';
import { ProgressBar } from '../components/common/ProgressBar';
import { DataTable } from '../components/common/DataTable';
import { EmptyState } from '../components/common/EmptyState';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { PageHeader } from '../components/common/PageHeader';
import { formatMoney } from '../lib/formatters';
import { cn } from '../lib/utils';
import type { ColumnDef, SortingState } from '@tanstack/react-table';
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

function SupplierFormModal({
  open,
  onOpenChange,
  supplier,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  supplier?: any;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState({
    name: supplier?.name || '',
    type: supplier?.type || 'unknown',
    website: supplier?.website || '',
    email: supplier?.email || '',
    phone: supplier?.phone || '',
    telegram: supplier?.telegram || '',
    whatsapp: supplier?.whatsapp || '',
    inn: supplier?.inn || '',
    kpp: supplier?.kpp || '',
    ogrn: supplier?.ogrn || '',
    legal_address: supplier?.legal_address || '',
    tags: supplier?.tags?.join(', ') || '',
    notes: supplier?.notes || '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      toast.error('Название обязательно');
      return;
    }
    setIsLoading(true);
    try {
      const data = {
        name: form.name.trim(),
        type: form.type,
        website: form.website.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        telegram: form.telegram.trim(),
        whatsapp: form.whatsapp.trim(),
        inn: form.inn.trim(),
        kpp: form.kpp.trim(),
        ogrn: form.ogrn.trim(),
        legal_address: form.legal_address.trim(),
        tags: form.tags ? form.tags.split(',').map((t: string) => t.trim()).filter(Boolean) : [],
        notes: form.notes.trim(),
      };
      if (supplier?.id) {
        await suppliersApi.patch(supplier.id, data);
        toast.success('Поставщик обновлён');
      } else {
        await suppliersApi.create(data);
        toast.success('Поставщик создан');
      }
      onSuccess();
      onOpenChange(false);
    } catch (error: any) {
      const message = error.response?.data?.error?.message || 'Не удалось сохранить';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{supplier ? 'Редактировать поставщика' : 'Новый поставщик'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Название *</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="ООО «Компания»" />
          </div>
          <div>
            <Label>Тип</Label>
            <Select value={form.type} onValueChange={(value) => setForm({ ...form, type: value })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manufacturer">Производитель</SelectItem>
                <SelectItem value="distributor">Дистрибьютор</SelectItem>
                <SelectItem value="wholesaler">Оптовик</SelectItem>
                <SelectItem value="retail">Розница</SelectItem>
                <SelectItem value="unknown">Неизвестно</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Email</Label>
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="sales@company.ru" />
            </div>
            <div>
              <Label>Телефон</Label>
              <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+7 (900) 000-00-00" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Telegram</Label>
              <Input value={form.telegram} onChange={(e) => setForm({ ...form, telegram: e.target.value })} placeholder="@username" />
            </div>
            <div>
              <Label>WhatsApp</Label>
              <Input value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} placeholder="+7 (900) 000-00-00" />
            </div>
          </div>
          <div>
            <Label>Сайт</Label>
            <Input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} placeholder="https://company.ru" />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label>ИНН</Label>
              <Input value={form.inn} onChange={(e) => setForm({ ...form, inn: e.target.value })} placeholder="1234567890" />
            </div>
            <div>
              <Label>КПП</Label>
              <Input value={form.kpp} onChange={(e) => setForm({ ...form, kpp: e.target.value })} placeholder="123456789" />
            </div>
            <div>
              <Label>ОГРН</Label>
              <Input value={form.ogrn} onChange={(e) => setForm({ ...form, ogrn: e.target.value })} placeholder="1234567890123" />
            </div>
          </div>
          <div>
            <Label>Юридический адрес</Label>
            <Input value={form.legal_address} onChange={(e) => setForm({ ...form, legal_address: e.target.value })} placeholder="г. Москва, ул. ..." />
          </div>
          <div>
            <Label>Теги (через запятую)</Label>
            <Input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="оргтехника, ноутбуки" />
          </div>
          <div>
            <Label>Заметки</Label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm"
              placeholder="Заметки о поставщике..."
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Отмена
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? 'Сохранение...' : supplier ? 'Сохранить' : 'Создать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SupplierMergeDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}) {
  const [primaryId, setPrimaryId] = useState('');
  const [secondaryId, setSecondaryId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const suppliersQuery = useQuery({
    queryKey: ['suppliers', 'all'],
    queryFn: () => suppliersApi.list({ per_page: 100 }),
    enabled: open,
  });

  const handleMerge = async () => {
    if (!primaryId || !secondaryId) {
      toast.error('Выберите обоих поставщиков');
      return;
    }
    if (primaryId === secondaryId) {
      toast.error('Нельзя объединить одного и того же поставщика');
      return;
    }
    setIsLoading(true);
    try {
      await suppliersApi.merge({ primary_id: primaryId, secondary_id: secondaryId });
      toast.success('Поставщики объединены');
      onSuccess();
      onOpenChange(false);
      setPrimaryId('');
      setSecondaryId('');
    } catch (error) {
      toast.error('Не удалось объединить');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Объединение поставщиков</DialogTitle>
          <DialogDescription>
            Данные вторичного поставщика будут перенесены в первичного. Вторичный будет удалён.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Первичный (останется)</Label>
            <Select value={primaryId} onValueChange={setPrimaryId}>
              <SelectTrigger>
                <SelectValue placeholder="Выберите поставщика" />
              </SelectTrigger>
              <SelectContent>
                {(suppliersQuery.data?.data || []).map((s: any) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Вторичный (будет удалён)</Label>
            <Select value={secondaryId} onValueChange={setSecondaryId}>
              <SelectTrigger>
                <SelectValue placeholder="Выберите поставщика" />
              </SelectTrigger>
              <SelectContent>
                {(suppliersQuery.data?.data || []).map((s: any) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Отмена
          </Button>
          <Button onClick={handleMerge} disabled={isLoading}>
            {isLoading ? 'Объединение...' : 'Объединить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function SuppliersPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [formModal, setFormModal] = useState<{ open: boolean; supplier?: any }>({ open: false });
  const [mergeModalOpen, setMergeModalOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<{ open: boolean; supplier?: any }>({ open: false });
  const [isDeleting, setIsDeleting] = useState(false);

  const filters = useMemo(() => ({
    search: searchParams.get('search') || '',
    type: searchParams.get('type') || '',
    tags: searchParams.get('tags') || '',
    has_email: searchParams.get('has_email') === 'true',
    has_phone: searchParams.get('has_phone') === 'true',
    is_active: searchParams.get('is_active') === 'true' || !searchParams.has('is_active'),
    min_successful_deals: searchParams.get('min_successful_deals') || '',
    created_after: searchParams.get('created_after') || '',
    sort_by: searchParams.get('sort_by') || 'created_at',
    sort_order: (searchParams.get('sort_order') as 'asc' | 'desc') || 'desc',
    page: Number(searchParams.get('page') || 1),
    per_page: Number(searchParams.get('per_page') || 20),
  }), [searchParams]);

  const suppliersQuery = useQuery({
    queryKey: ['suppliers', 'list', filters],
    queryFn: () =>
      suppliersApi.list({
        search: filters.search || undefined,
        type: filters.type || undefined,
        tags: filters.tags || undefined,
        has_email: filters.has_email || undefined,
        has_phone: filters.has_phone || undefined,
        is_active: filters.is_active,
        min_successful_deals: filters.min_successful_deals ? Number(filters.min_successful_deals) : undefined,
        created_after: filters.created_after || undefined,
        sort_by: filters.sort_by,
        sort_order: filters.sort_order,
        page: filters.page,
        per_page: filters.per_page,
      }),
  });

  const updateFilters = useCallback((updates: Record<string, string | null>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === '') {
        newParams.delete(key);
      } else {
        newParams.set(key, value);
      }
    });
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  const resetFilters = useCallback(() => {
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  const handleDelete = async () => {
    if (!confirmDelete.supplier) return;
    setIsDeleting(true);
    try {
      await suppliersApi.delete(confirmDelete.supplier.id);
      toast.success('Поставщик деактивирован');
      setConfirmDelete({ open: false });
      suppliersQuery.refetch();
    } catch (error) {
      toast.error('Не удалось деактивировать');
    } finally {
      setIsDeleting(false);
    }
  };

  const columns: ColumnDef<SupplierListItem, any>[] = useMemo(
    () => [
      {
        id: 'name',
        header: 'Название',
        accessorKey: 'name',
        cell: ({ row }) => (
          <div>
            <button
              onClick={() => navigate(`/suppliers/${row.original.id}`)}
              className="text-sm font-medium text-blue-600 hover:text-blue-700 hover:underline text-left"
            >
              {row.original.name}
            </button>
            {row.original.website && (
              <a
                href={row.original.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 text-xs text-slate-400 hover:text-slate-600 ml-2"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </a>
            )}
          </div>
        ),
        size: 300,
      },
      {
        id: 'type',
        header: 'Тип',
        accessorKey: 'type',
        cell: ({ row }) => <TypeBadge type={row.original.type} size="sm" />,
        size: 110,
      },
      {
        id: 'email',
        header: 'Email',
        accessorKey: 'email',
        cell: ({ row }) => (
          row.original.email ? (
            <a href={`mailto:${row.original.email}`} className="text-sm text-slate-600 hover:text-blue-600">
              {row.original.email}
            </a>
          ) : (
            <span className="text-slate-400">—</span>
          )
        ),
        size: 180,
        enableSorting: false,
      },
      {
        id: 'phone',
        header: 'Телефон',
        accessorKey: 'phone',
        cell: ({ row }) => (
          row.original.phone ? (
            <span className="text-sm text-slate-600">{row.original.phone}</span>
          ) : (
            <span className="text-slate-400">—</span>
          )
        ),
        size: 140,
        enableSorting: false,
      },
      {
        id: 'tags',
        header: 'Теги',
        accessorKey: 'tags',
        cell: ({ row }) => (
          <div className="flex gap-1 flex-wrap max-w-[180px]">
            {(row.original.tags || []).slice(0, 3).map((tag: string) => (
              <TagChip key={tag} label={tag} />
            ))}
            {(row.original.tags || []).length > 3 && (
              <span className="text-xs text-slate-400">+{(row.original.tags || []).length - 3}</span>
            )}
          </div>
        ),
        size: 150,
        enableSorting: false,
      },
      {
        id: 'response_rate',
        header: 'Ответ',
        accessorKey: 'rating.response_rate',
        cell: ({ row }) => (
          <div className="w-20">
            <ProgressBar value={(row.original.rating?.response_rate || 0) * 100} size="sm" showLabel />
          </div>
        ),
        size: 100,
        enableSorting: false,
      },
      {
        id: 'deals',
        header: 'Сделки',
        accessorKey: 'successful_deals',
        cell: ({ row }) => (
          <span className="text-sm text-slate-600">
            {row.original.successful_deals}/{row.original.total_lots}
          </span>
        ),
        size: 70,
      },
      {
        id: 'volume',
        header: 'Объём',
        accessorKey: 'total_volume_rub',
        cell: ({ row }) => (
          <span className="text-sm text-slate-600">{formatMoney(row.original.total_volume_rub)}</span>
        ),
        size: 100,
      },
      {
        id: 'is_active',
        header: 'Активен',
        accessorKey: 'is_active',
        cell: ({ row }) => (
          <Switch
            checked={row.original.is_active}
            onCheckedChange={async (checked) => {
              try {
                await suppliersApi.patch(row.original.id, { is_active: checked });
                toast.success(checked ? 'Поставщик активирован' : 'Поставщик деактивирован');
                suppliersQuery.refetch();
              } catch {
                toast.error('Не удалось изменить статус');
              }
            }}
            onClick={(e) => e.stopPropagation()}
          />
        ),
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
              <DropdownMenuItem onClick={() => navigate(`/suppliers/${row.original.id}`)}>
                <Building2 className="h-4 w-4 mr-2" aria-hidden="true" />
                Открыть карточку
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setFormModal({ open: true, supplier: row.original })}>
                <Pencil className="h-4 w-4 mr-2" aria-hidden="true" />
                Редактировать
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setConfirmDelete({ open: true, supplier: row.original })}>
                <Trash2 className="h-4 w-4 mr-2 text-red-500" aria-hidden="true" />
                Деактивировать
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ),
        size: 40,
        enableSorting: false,
      },
    ],
    [navigate, suppliersQuery]
  );

  const suppliers = suppliersQuery.data?.data || [];
  const meta = suppliersQuery.data?.meta;

  return (
    <div>
      <PageHeader
        title="Поставщики"
        description={`Всего: ${meta?.total || 0}`}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setMergeModalOpen(true)}>
              <GitMerge className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Объединить
            </Button>
            <Button variant="outline" size="sm" onClick={() => suppliersQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Обновить
            </Button>
            <Button variant="outline" size="sm" onClick={() => setShowFilters(!showFilters)}>
              <Search className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Фильтры
            </Button>
            <Button size="sm" onClick={() => setFormModal({ open: true })}>
              <Plus className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Добавить
            </Button>
          </>
        }
      />

      {showFilters && (
        <div className="rounded-lg border border-slate-200 p-4 mb-6 bg-white">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            <div>
              <Label className="text-xs text-slate-500">Поиск</Label>
              <Input
                placeholder="Название, email, ИНН, телефон"
                defaultValue={filters.search}
                onChange={(e) => {
                  const timer = setTimeout(() => updateFilters({ search: e.target.value, page: '1' }), 300);
                  return () => clearTimeout(timer);
                }}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Тип</Label>
              <Select value={filters.type || 'all'} onValueChange={(value) => updateFilters({ type: value === 'all' ? '' : value, page: '1' })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Все</SelectItem>
                  <SelectItem value="manufacturer">Производитель</SelectItem>
                  <SelectItem value="distributor">Дистрибьютор</SelectItem>
                  <SelectItem value="wholesaler">Оптовик</SelectItem>
                  <SelectItem value="retail">Розница</SelectItem>
                  <SelectItem value="unknown">Неизвестно</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Теги (через запятую)</Label>
              <Input
                placeholder="оргтехника,ноутбуки"
                defaultValue={filters.tags}
                onChange={(e) => updateFilters({ tags: e.target.value, page: '1' })}
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs text-slate-500">Мин. сделок</Label>
              <Input
                type="number"
                min={0}
                placeholder="0"
                defaultValue={filters.min_successful_deals}
                onChange={(e) => updateFilters({ min_successful_deals: e.target.value, page: '1' })}
                className="mt-1"
              />
            </div>
            <div className="flex items-end gap-4 pb-1">
              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_email}
                  onCheckedChange={(checked) => updateFilters({ has_email: checked ? 'true' : '', page: '1' })}
                />
                Есть email
              </label>
              <label className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_phone}
                  onCheckedChange={(checked) => updateFilters({ has_phone: checked ? 'true' : '', page: '1' })}
                />
                Есть телефон
              </label>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Сортировка</Label>
              <Select value={filters.sort_by} onValueChange={(value) => updateFilters({ sort_by: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at">По дате создания</SelectItem>
                  <SelectItem value="name">По названию</SelectItem>
                  <SelectItem value="successful_deals">По успешным сделкам</SelectItem>
                  <SelectItem value="total_volume_rub">По объёму</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-slate-500">Порядок</Label>
              <Select value={filters.sort_order} onValueChange={(value) => updateFilters({ sort_order: value })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="desc">По убыванию</SelectItem>
                  <SelectItem value="asc">По возрастанию</SelectItem>
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

      {suppliersQuery.isLoading ? (
        <LoadingSkeleton rows={10} cols={7} type="table" />
      ) : suppliersQuery.isError ? (
        <ErrorAlert message="Не удалось загрузить поставщиков" onRetry={() => suppliersQuery.refetch()} />
      ) : (
        <DataTable
          data={suppliers}
          columns={columns}
          page={filters.page}
          pageCount={meta?.pages || 1}
          total={meta?.total}
          perPage={filters.per_page}
          onPageChange={(page) => updateFilters({ page: String(page) })}
          onPerPageChange={(perPage) => updateFilters({ per_page: String(perPage), page: '1' })}
          sorting={sorting}
          onSortingChange={setSorting}
          onRowClick={(row) => navigate(`/suppliers/${row.id}`)}
          enableVirtualization
          tableHeight={600}
          emptyState={
            <EmptyState
              icon={Building2}
              title="Поставщики не найдены"
              description="Попробуйте изменить фильтры или добавьте нового поставщика"
              actionLabel="Добавить поставщика"
              onAction={() => setFormModal({ open: true })}
            />
          }
        />
      )}

      <SupplierFormModal
        open={formModal.open}
        onOpenChange={(open) => setFormModal((prev) => ({ ...prev, open }))}
        supplier={formModal.supplier}
        onSuccess={() => suppliersQuery.refetch()}
      />
      <SupplierMergeDialog
        open={mergeModalOpen}
        onOpenChange={setMergeModalOpen}
        onSuccess={() => suppliersQuery.refetch()}
      />
      <ConfirmDialog
        open={confirmDelete.open}
        onOpenChange={(open) => setConfirmDelete((prev) => ({ ...prev, open }))}
        title="Деактивировать поставщика"
        description={confirmDelete.supplier ? `«${confirmDelete.supplier.name}» будет деактивирован.` : ''}
        confirmLabel="Деактивировать"
        variant="destructive"
        isLoading={isDeleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}