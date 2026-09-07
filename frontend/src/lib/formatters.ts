import { format, formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';

export function formatDate(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  return format(new Date(isoString), 'dd.MM.yyyy');
}

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  return format(new Date(isoString), 'dd.MM.yyyy HH:mm');
}

export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  return formatDistanceToNow(new Date(isoString), { addSuffix: true, locale: ru });
}

export function formatMoney(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return '—';
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(1)}%`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('ru-RU').format(value);
}