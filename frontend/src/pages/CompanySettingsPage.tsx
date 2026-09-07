import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Building, RefreshCw, Save, AlertCircle, CheckCircle2 } from 'lucide-react';
import { settingsApi } from '../api/settings';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { PageHeader } from '../components/common/PageHeader';
import { cn } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';

export function CompanySettingsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    legal_name: '',
    inn: '',
    kpp: '',
    ogrn: '',
    legal_address: '',
    contact_person: '',
    contact_email: '',
    contact_phone: '',
    email_signature: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const companyQuery = useQuery({
    queryKey: ['settings', 'company'],
    queryFn: () => settingsApi.getSection('company'),
  });

  useEffect(() => {
    if (companyQuery.data) {
      const data = companyQuery.data;
      setForm({
        legal_name: data.legal_name || '',
        inn: data.inn || '',
        kpp: data.kpp || '',
        ogrn: data.ogrn || '',
        legal_address: data.legal_address || '',
        contact_person: data.contact_person || '',
        contact_email: data.contact_email || '',
        contact_phone: data.contact_phone || '',
        email_signature: data.email_signature || '',
      });
    }
  }, [companyQuery.data]);

  const saveMutation = useMutation({
    mutationFn: (data: any) => settingsApi.putSection('company', data),
    onSuccess: () => {
      toast.success('Данные компании сохранены');
      queryClient.invalidateQueries({ queryKey: ['settings', 'company'] });
    },
    onError: () => toast.error('Не удалось сохранить'),
  });

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!form.legal_name.trim()) newErrors.legal_name = 'Обязательное поле';
    if (form.inn && !/^\d{10}$|^\d{12}$/.test(form.inn)) newErrors.inn = 'ИНН должен содержать 10 или 12 цифр';
    if (form.kpp && !/^\d{9}$/.test(form.kpp)) newErrors.kpp = 'КПП должен содержать 9 цифр';
    if (form.ogrn && !/^\d{13}$|^\d{15}$/.test(form.ogrn)) newErrors.ogrn = 'ОГРН должен содержать 13 или 15 цифр';
    if (form.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.contact_email)) newErrors.contact_email = 'Неверный email';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = () => {
    if (!validate()) return;
    saveMutation.mutate({
      legal_name: form.legal_name.trim(),
      inn: form.inn.trim(),
      kpp: form.kpp.trim(),
      ogrn: form.ogrn.trim(),
      legal_address: form.legal_address.trim(),
      contact_person: form.contact_person.trim(),
      contact_email: form.contact_email.trim(),
      contact_phone: form.contact_phone.trim(),
      email_signature: form.email_signature,
    });
  };

  if (companyQuery.isLoading) return <LoadingSkeleton rows={6} cols={2} type="form" />;
  if (companyQuery.isError) return <ErrorAlert message="Не удалось загрузить настройки" onRetry={() => companyQuery.refetch()} />;

  return (
    <div>
      <PageHeader
        title="Компания"
        description="Данные компании для легенды в коммуникации с поставщиками"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => companyQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Сбросить
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saveMutation.isPending}>
              <Save className="h-3.5 w-3.5 mr-1.5" />
              {saveMutation.isPending ? 'Сохранение...' : 'Сохранить'}
            </Button>
          </>
        }
      />
      <div className="max-w-2xl">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2 mb-4">
            <Building className="h-5 w-5 text-slate-500" />
            <h3 className="text-base font-semibold text-slate-900">Реквизиты</h3>
          </div>
          <div className="space-y-4">
            <div>
              <Label>Название юрлица / ИП *</Label>
              <Input value={form.legal_name} onChange={(e) => setForm({ ...form, legal_name: e.target.value })} placeholder="ООО «Рога и Копыта»" className={cn('mt-1', errors.legal_name && 'border-red-300')} />
              {errors.legal_name && <p className="text-xs text-red-600 mt-1">{errors.legal_name}</p>}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>ИНН</Label>
                <Input value={form.inn} onChange={(e) => setForm({ ...form, inn: e.target.value.replace(/\D/g, '') })} placeholder="1234567890" maxLength={12} className={cn('mt-1 font-mono', errors.inn && 'border-red-300')} />
                {errors.inn && <p className="text-xs text-red-600 mt-1">{errors.inn}</p>}
              </div>
              <div>
                <Label>КПП</Label>
                <Input value={form.kpp} onChange={(e) => setForm({ ...form, kpp: e.target.value.replace(/\D/g, '') })} placeholder="123456789" maxLength={9} className={cn('mt-1 font-mono', errors.kpp && 'border-red-300')} />
                {errors.kpp && <p className="text-xs text-red-600 mt-1">{errors.kpp}</p>}
              </div>
              <div>
                <Label>ОГРН</Label>
                <Input value={form.ogrn} onChange={(e) => setForm({ ...form, ogrn: e.target.value.replace(/\D/g, '') })} placeholder="1234567890123" maxLength={15} className={cn('mt-1 font-mono', errors.ogrn && 'border-red-300')} />
                {errors.ogrn && <p className="text-xs text-red-600 mt-1">{errors.ogrn}</p>}
              </div>
            </div>
            <div>
              <Label>Юридический адрес</Label>
              <Input value={form.legal_address} onChange={(e) => setForm({ ...form, legal_address: e.target.value })} placeholder="г. Москва, ул. Примерная, д. 1" className="mt-1" />
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 mt-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="h-5 w-5 text-slate-500" />
            <h3 className="text-base font-semibold text-slate-900">Контактное лицо</h3>
          </div>
          <div className="space-y-4">
            <div>
              <Label>Имя</Label>
              <Input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} placeholder="Иван Иванов" className="mt-1" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Email</Label>
                <Input type="email" value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} placeholder="ivan@example.com" className={cn('mt-1', errors.contact_email && 'border-red-300')} />
                {errors.contact_email && <p className="text-xs text-red-600 mt-1">{errors.contact_email}</p>}
              </div>
              <div>
                <Label>Телефон</Label>
                <Input value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} placeholder="+7 (999) 123-45-67" className="mt-1" />
              </div>
            </div>
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 mt-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="h-5 w-5 text-slate-500" />
            <h3 className="text-base font-semibold text-slate-900">Подпись в письмах</h3>
          </div>
          <div>
            <Label>Подпись</Label>
            <Textarea value={form.email_signature} onChange={(e) => setForm({ ...form, email_signature: e.target.value })} placeholder={'С уважением,\nИван Иванов\nООО «Рога и Копыта»'} rows={4} className="mt-1" />
            <p className="text-xs text-slate-400 mt-1">Используется в конце автоматических писем поставщикам</p>
          </div>
        </div>
        {saveMutation.isError && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">Не удалось сохранить. Попробуйте снова.</div>
        )}
      </div>
    </div>
  );
}