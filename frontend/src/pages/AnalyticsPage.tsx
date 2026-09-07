import { useQuery } from '@tanstack/react-query';
import { RefreshCw, BarChart3 } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts';
import { tendersApi, type TenderStats } from '../api/tenders';
import { suppliersApi } from '../api/suppliers';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { EmptyState } from '../components/common/EmptyState';
import { PageHeader } from '../components/common/PageHeader';
import { Button } from '../components/ui/button';
import { formatMoney } from '../lib/formatters';

const COLORS = ['#2563EB', '#16A34A', '#D97706', '#7E22CE', '#DC2626', '#0891B2', '#DB2777', '#65A30D', '#EA580C', '#4F46E5'];

function FunnelChart({ stats }: { stats: TenderStats }) {
  const byStatus = stats?.by_status || {};
  const funnelData = [
    { name: 'Всего', value: stats?.total || 0, fill: '#94A3B8' },
    { name: 'Релевантные', value: ['RELEVANT','UNCERTAIN','SCORING','SCORED','AWAITING_SUPPLIER_SEARCH','SUPPLIER_SEARCH_IN_PROGRESS','SUPPLIERS_FOUND','NO_SUPPLIERS_FOUND','AWAITING_CP','CP_REQUESTED','CP_PARTIALLY_RECEIVED','CP_FULLY_RECEIVED','NEGOTIATING','READY_FOR_DECISION','APPROVED','REJECTED'].reduce((acc, s) => acc + (byStatus[s]||0), 0), fill: '#3B82F6' },
    { name: 'С поставщиками', value: ['SUPPLIERS_FOUND','AWAITING_CP','CP_REQUESTED','CP_PARTIALLY_RECEIVED','CP_FULLY_RECEIVED','NEGOTIATING','READY_FOR_DECISION','APPROVED','REJECTED'].reduce((acc, s) => acc + (byStatus[s]||0), 0), fill: '#60A5FA' },
    { name: 'С КП', value: ['CP_PARTIALLY_RECEIVED','CP_FULLY_RECEIVED','NEGOTIATING','READY_FOR_DECISION','APPROVED','REJECTED'].reduce((acc, s) => acc + (byStatus[s]||0), 0), fill: '#93C5FD' },
    { name: 'Готовы к решению', value: (byStatus['READY_FOR_DECISION']||0) + (byStatus['APPROVED']||0) + (byStatus['REJECTED']||0), fill: '#BFDBFE' },
    { name: 'Одобрены', value: byStatus['APPROVED']||0, fill: '#22C55E' },
  ];
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-base font-semibold text-slate-900 mb-4">Воронка конверсии</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={funnelData} layout="vertical" margin={{ left: 120, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis type="number" stroke="#94A3B8" />
          <YAxis type="category" dataKey="name" stroke="#64748B" width={110} tick={{ fontSize: 12 }} />
          <RechartsTooltip formatter={(value: any) => [value.toLocaleString('ru-RU'), 'Количество']} contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }} />
          <Bar dataKey="value" fill="#3B82F6" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CategoryPieChart({ stats }: { stats: TenderStats }) {
  const categories = stats?.by_category || [];
  const data = categories.slice(0, 10).map((cat: any) => ({ name: cat.category_name, value: cat.count }));
  if (data.length === 0) return <div className="rounded-lg border border-slate-200 bg-white p-4"><h3 className="text-base font-semibold text-slate-900 mb-4">Распределение по категориям</h3><EmptyState title="Нет данных" description="Категории ещё не накопились" /></div>;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-base font-semibold text-slate-900 mb-4">Распределение по категориям (топ-10)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" labelLine={false} outerRadius={100} fill="#8884d8" dataKey="value" label={({ name, percent }: any) => `${name}: ${(percent * 100).toFixed(0)}%`}>
            {data.map((entry: any, index: number) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
          </Pie>
          <RechartsTooltip formatter={(value: any) => [value.toLocaleString('ru-RU'), 'Тендеров']} contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }} />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-2 mt-3">
        {data.map((entry: any, index: number) => (
          <div key={index} className="flex items-center gap-1.5 text-xs text-slate-600">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
            {entry.name}
          </div>
        ))}
      </div>
    </div>
  );
}

function TrendLineChart() {
  const placeholderData = [
    { date: '01.08', new: 120, approved: 2 },
    { date: '02.08', new: 145, approved: 3 },
    { date: '03.08', new: 98, approved: 1 },
    { date: '04.08', new: 150, approved: 5 },
    { date: '05.08', new: 180, approved: 4 },
    { date: '06.08', new: 165, approved: 3 },
    { date: '07.08', new: 200, approved: 6 },
  ];
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between mb-4"><h3 className="text-base font-semibold text-slate-900">Динамика тендеров</h3><span className="text-xs text-slate-400 bg-slate-50 rounded-full px-2 py-0.5">демо-данные</span></div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={placeholderData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis dataKey="date" stroke="#94A3B8" />
          <YAxis stroke="#94A3B8" />
          <RechartsTooltip contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }} />
          <Legend />
          <Line type="monotone" dataKey="new" name="Новых" stroke="#3B82F6" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="approved" name="Одобрено" stroke="#22C55E" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function TopSuppliersChart() {
  const suppliersQuery = useQuery({
    queryKey: ['suppliers', 'top'],
    queryFn: () => suppliersApi.list({ per_page: 100, sort_by: 'total_volume_rub', sort_order: 'desc' }),
  });
  if (suppliersQuery.isLoading) return <LoadingSkeleton rows={3} cols={1} type="card" />;
  if (suppliersQuery.isError) return <ErrorAlert message="Не удалось загрузить данные" onRetry={() => suppliersQuery.refetch()} />;
  const suppliers = (suppliersQuery.data?.data || []).slice(0, 10);
  const data = suppliers.map((s: any) => ({ name: s.name.length > 20 ? s.name.slice(0, 20) + '...' : s.name, volume: s.total_volume_rub || 0 }));
  if (data.length === 0) return <div className="rounded-lg border border-slate-200 bg-white p-4"><h3 className="text-base font-semibold text-slate-900 mb-4">Топ поставщиков по объёму</h3><EmptyState title="Нет данных" description="Поставщики ещё не накопились" /></div>;
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-base font-semibold text-slate-900 mb-4">Топ-10 поставщиков по объёму</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} layout="vertical" margin={{ left: 140, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis type="number" stroke="#94A3B8" tickFormatter={(value: number) => `${(value / 1000000).toFixed(1)} млн`} />
          <YAxis type="category" dataKey="name" stroke="#64748B" width={130} tick={{ fontSize: 11 }} />
          <RechartsTooltip formatter={(value: any) => [formatMoney(value), 'Объём']} contentStyle={{ borderRadius: '8px', border: '1px solid #E2E8F0' }} />
          <Bar dataKey="volume" fill="#7E22CE" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function AnalyticsPage() {
  const statsQuery = useQuery({
    queryKey: ['tenders', 'stats'],
    queryFn: () => tendersApi.stats(),
  });
  if (statsQuery.isLoading) return <LoadingSkeleton rows={3} cols={2} type="card" />;
  if (statsQuery.isError) return <ErrorAlert message="Не удалось загрузить статистику" onRetry={() => statsQuery.refetch()} />;
  const stats = statsQuery.data!;
  return (
    <div>
      <PageHeader title="Аналитика" description="Статистика работы системы" actions={<Button variant="outline" size="sm" onClick={() => statsQuery.refetch()}><RefreshCw className="h-3.5 w-3.5 mr-1.5" />Обновить</Button>} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <FunnelChart stats={stats} />
        <CategoryPieChart stats={stats} />
        <TrendLineChart />
        <TopSuppliersChart />
      </div>
    </div>
  );
}