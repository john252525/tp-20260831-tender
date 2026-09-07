import { formatMoney, formatDate, formatPercent, formatNumber } from '../formatters';

describe('formatters', () => {
  test('formatMoney форматирует рубли без десятичных', () => {
    expect(formatMoney(1500000)).toBe('1\u00A0500\u00A0000\u00A0₽');
  });

  test('formatMoney возвращает прочерк для null/undefined', () => {
    expect(formatMoney(null)).toBe('—');
    expect(formatMoney(undefined)).toBe('—');
  });

  test('formatDate форматирует ISO дату', () => {
    expect(formatDate('2026-08-15T00:00:00Z')).toBe('15.08.2026');
  });

  test('formatPercent добавляет знак процента', () => {
    expect(formatPercent(22.5)).toBe('22.5%');
  });

  test('formatNumber форматирует с разделителями', () => {
    expect(formatNumber(12500)).toBe('12\u00A0500');
  });
});