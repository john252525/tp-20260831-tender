import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../StatusBadge';

describe('StatusBadge', () => {
  test('рендерит статус NEW', () => {
    render(<StatusBadge status="NEW" />);
    expect(screen.getByText('Новый')).toBeInTheDocument();
  });

  test('рендерит статус RELEVANT', () => {
    render(<StatusBadge status="RELEVANT" />);
    expect(screen.getByText('Релевантный')).toBeInTheDocument();
  });

  test('рендерит неизвестный статус как есть', () => {
    render(<StatusBadge status="UNKNOWN_STATUS" />);
    expect(screen.getByText('UNKNOWN_STATUS')).toBeInTheDocument();
  });

  test('имеет класс для APPROVED (белый текст на зелёном)', () => {
    render(<StatusBadge status="APPROVED" />);
    const badge = screen.getByText('Одобрен').closest('span');
    expect(badge).toHaveClass('bg-green-600');
    expect(badge).toHaveClass('text-white');
  });

  test('имеет класс для UNCERTAIN (жёлтый фон, тёмный текст)', () => {
    render(<StatusBadge status="UNCERTAIN" />);
    const badge = screen.getByText('Под вопросом').closest('span');
    expect(badge).toHaveClass('bg-yellow-100');
    expect(badge).toHaveClass('text-yellow-700');
  });
});