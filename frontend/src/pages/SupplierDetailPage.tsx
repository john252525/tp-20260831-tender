import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ArrowLeft,
  Building2,
  Mail,
  Phone,
  Send,
  Globe,
  FileText,
  RefreshCw,
  Trash2,
  Package,
  CheckCircle2,
  TrendingUp,
} from 'lucide-react';
import { suppliersApi } from '../api/suppliers';
import { TypeBadge } from '../components/common/TypeBadge';
import { TagChip } from '../components/common/TagChip';
import { StatusBadge } from '../components/common/StatusBadge';
import { ProgressBar } from '../components/common/ProgressBar';
import { StatCard } from '../components/common/StatCard';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { formatMoney, formatDate, formatDateTime } from '../lib/formatters';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { cn } from '../lib/utils';

function SupplierOverviewTab({ supplier }: { supplier: any }) {
  const rating = supplier?.rating || {};
  const statistics = supplier?.statistics || {};
  const contacts = supplier?.contacts || supplier || {};
  const legalInfo = supplier?.legal_info || supplier || {};
  const contactPersons = contacts.contact_persons || [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-4">Контакты</h3>
          <dl className="space-y-3">
            {contacts.email && (
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-slate-400 flex-shrink-0" aria-hidden="true" />
                <a href={`mailto:${contacts.email}`} className="text-sm text-blue-600 hover:underline">{contacts.email}</a>
              </div>
            )}
            {contacts.phone && (
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-slate-400 flex-shrink-0" aria-hidden="true" />
                <span className="text-sm text-slate-700">{contacts.phone}</span>
              </div>
            )}
            {contacts.telegram && (
              <div className="flex items-center gap-2">
                <Send className="h-4 w-4 text-slate-400 flex-shrink-0" aria-hidden="true" />
                <span className="text-sm text-slate-700">{contacts.telegram}</span>
              </div>
            )}
            {supplier?.website && (
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-slate-400 flex-shrink-0" aria-hidden="true" />
                <a href={supplier.website} target="_blank" rel="noopener noreferrer" className="text-sm text-blue-600 hover:underline">{supplier.website}</a>
              </div>
            )}
            {contactPersons.length > 0 && (
              <div className="pt-3 border-t border-slate-100">
                <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Контактные лица</p>
                <div className="space-y-2">
                  {contactPersons.map((person: any, index: number) => (
                    <div key={index} className="text-sm">
                      <p className="font-medium text-slate-900">{person.name}</p>
                      {person.position && <p className="text-xs text-slate-500">{person.position}</p>}
                      <p className="text-xs text-slate-600">
                        {person.email && <span className="mr-2">{person.email}</span>}
                        {person.phone && <span>{person.phone}</span>}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </dl>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-4">Юридическая информация</h3>
          <dl className="space-y-3">
            <div>
              <dt className="text-xs text-slate-500">ИНН</dt>
              <dd className="text-sm font-mono text-slate-900">{legalInfo.inn || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">КПП</dt>
              <dd className="text-sm font-mono text-slate-900">{legalInfo.kpp || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">ОГРН</dt>
              <dd className="text-sm font-mono text-slate-900">{legalInfo.ogrn || '—'}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Юридический адрес</dt>
              <dd className="text-sm text-slate-900">{legalInfo.legal_address || '—'}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="text-base font-semibold text-slate-900 mb-4">Рейтинг</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-slate-500 mb-1">Скорость ответа</p>
            <p className="text-sm font-semibold text-slate-900 mb-1">{rating.avg_response_time_hours ? `${rating.avg_response_time_hours} ч` : '—'}</p>
            <ProgressBar value={rating.avg_response_time_hours ? Math.max(0, 100 - rating.avg_response_time_hours * 10) : 0} size="sm" />
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-1">Процент ответов</p>
            <p className="text-sm font-semibold text-slate-900 mb-1">{rating.response_rate ? `${(rating.response_rate * 100).toFixed(0)}%` : '—'}</p>
            <ProgressBar value={(rating.response_rate || 0) * 100} size="sm" />
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-1">Ценовая конкурентоспособность</p>
            <p className="text-sm font-semibold text-slate-900 mb-1">{rating.price_competitiveness ? `${(rating.price_competitiveness * 100).toFixed(0)}%` : '—'}</p>
            <ProgressBar value={(rating.price_competitiveness || 0) * 100} size="sm" />
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-1">Надёжность</p>
            <p className="text-sm font-semibold text-slate-900 mb-1">{rating.reliability ? `${(rating.reliability * 100).toFixed(0)}%` : '—'}</p>
            <ProgressBar value={(rating.reliability || 0) * 100} size="sm" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Всего лотов" value={statistics.total_lots || 0} icon={Package} iconBg="bg-slate-100" iconText="text-slate-600" />
        <StatCard title="КП получено" value={statistics.cp_received || 0} icon={FileText} iconBg="bg-blue-100" iconText="text-blue-700" />
        <StatCard title="Успешных сделок" value={statistics.successful_deals || 0} icon={CheckCircle2} iconBg="bg-green-100" iconText="text-green-700" />
        <StatCard title="Общий объём" value={formatMoney(statistics.total_volume_rub)} icon={TrendingUp} iconBg="bg-purple-100" iconText="text-purple-700" />
      </div>

      {supplier?.tags?.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Теги</p>
          <div className="flex gap-1.5 flex-wrap">
            {supplier.tags.map((tag: string) => <TagChip key={tag} label={tag} />)}
          </div>
        </div>
      )}

      {supplier?.notes && (
        <div className="rounded-lg border border-slate-200 bg-amber-50/50 p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Заметки</p>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{supplier.notes}</p>
        </div>
      )}
    </div>
  );
}

function SupplierHistoryTab({ recentTenders }: { recentTenders: any[] }) {
  if (!recentTenders || recentTenders.length === 0) {
    return <EmptyState icon={FileText} title="История пуста" description="У поставщика ещё нет связанных тендеров" />;
  }
  return (
    <div className="rounded-lg border border-slate-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Тендер</th>
            <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Статус</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Маржа</th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Дата</th>
          </tr>
        </thead>
        <tbody>
          {recentTenders.map((tender: any, index: number) => (
            <tr key={index} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="px-4 py-3 font-medium text-slate-900">{tender.tender_title}</td>
              <td className="px-4 py-3 text-center"><StatusBadge status={tender.status} size="sm" /></td>
              <td className="px-4 py-3 text-right">
                {tender.margin_percent ? <span className="font-medium text-green-600">{tender.margin_percent.toFixed(1)}%</span> : <span className="text-slate-400">—</span>}
              </td>
              <td className="px-4 py-3 text-right text-slate-600">{formatDate(tender.date)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SupplierCommunicationsTab({ supplierId }: { supplierId: string }) {
  const communicationsQuery = useQuery({
    queryKey: ['supplier', supplierId, 'communications'],
    queryFn: () => suppliersApi.getCommunications(supplierId),
  });

  if (communicationsQuery.isLoading) return <LoadingSkeleton rows={5} cols={1} type="card" />;
  if (communicationsQuery.isError) return <ErrorAlert message="Не удалось загрузить переписку" onRetry={() => communicationsQuery.refetch()} />;

  const communications = communicationsQuery.data || [];
  if (communications.length === 0) {
    return <EmptyState icon={Mail} title="Переписки нет" description="С этим поставщиком ещё не было коммуникаций" />;
  }

  return (
    <div className="space-y-3">
      {communications.map((comm: any) => (
        <div key={comm.id} className="rounded-lg border border-slate-200 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className={cn('text-xs font-medium rounded-full px-2 py-0.5', comm.direction === 'outgoing' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700')}>
              {comm.direction === 'outgoing' ? 'Исходящее' : 'Входящее'}
            </span>
            <span className="text-xs text-slate-400">{formatDateTime(comm.sent_at || comm.received_at)}</span>
          </div>
          <p className="text-sm font-medium text-slate-900">{comm.subject}</p>
          <p className="text-sm text-slate-600 mt-1 line-clamp-3">{comm.body_preview}</p>
        </div>
      ))}
    </div>
  );
}

export function SupplierDetailPage() {
  const { supplierId } = useParams<{ supplierId: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const supplierQuery = useQuery({
    queryKey: ['supplier', supplierId],
    queryFn: () => suppliersApi.get(supplierId!),
    enabled: !!supplierId,
  });

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await suppliersApi.delete(supplierId!);
      toast.success('Поставщик деактивирован');
      navigate('/suppliers');
    } catch {
      toast.error('Не удалось деактивировать');
    } finally {
      setIsDeleting(false);
    }
  };

  if (supplierQuery.isLoading) {
    return (
      <div>
        <LoadingSkeleton rows={3} cols={3} type="card" />
        <LoadingSkeleton rows={4} cols={4} type="table" />
      </div>
    );
  }
  if (supplierQuery.isError) {
    return <ErrorAlert message="Не удалось загрузить поставщика" onRetry={() => supplierQuery.refetch()} />;
  }

  const supplier = supplierQuery.data;

  return (
    <div>
      <div className="mb-6">
        <button onClick={() => navigate('/suppliers')} className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors mb-3">
          <ArrowLeft className="h-4 w-4" />
          Назад к поставщикам
        </button>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Building2 className="h-6 w-6 text-slate-500" />
              </div>
              <div className="min-w-0">
                <h1 className="text-2xl font-semibold text-slate-900 truncate">{supplier?.name}</h1>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <TypeBadge type={supplier?.type} />
                  {supplier?.inn && <span className="text-xs text-slate-500">ИНН: {supplier.inn}</span>}
                  <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', supplier?.is_active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500')}>
                    {supplier?.is_active ? 'Активен' : 'Неактивен'}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => supplierQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Обновить
            </Button>
            <Button variant="outline" size="sm" onClick={() => setConfirmDelete(true)}>
              <Trash2 className="h-3.5 w-3.5 mr-1.5 text-red-500" />
              Деактивировать
            </Button>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="border-b border-slate-200 w-full justify-start gap-1 rounded-none bg-transparent p-0">
          <TabsTrigger value="overview" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Обзор
          </TabsTrigger>
          <TabsTrigger value="history" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            История ({supplier?.recent_tenders?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="communications" className="data-[state=active]:border-blue-600 data-[state=active]:text-blue-700 border-b-2 border-transparent rounded-none px-4 py-2.5 text-sm font-medium">
            Переписка
          </TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-4">
          <SupplierOverviewTab supplier={supplier} />
        </TabsContent>
        <TabsContent value="history" className="mt-4">
          <SupplierHistoryTab recentTenders={supplier?.recent_tenders || []} />
        </TabsContent>
        <TabsContent value="communications" className="mt-4">
          <SupplierCommunicationsTab supplierId={supplierId!} />
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={confirmDelete}
        onOpenChange={setConfirmDelete}
        title="Деактивировать поставщика"
        description={`«${supplier?.name}» будет деактивирован.`}
        confirmLabel="Деактивировать"
        variant="destructive"
        isLoading={isDeleting}
        onConfirm={handleDelete}
      />
    </div>
  );
}