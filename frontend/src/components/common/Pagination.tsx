import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '../../lib/utils';

interface PaginationProps {
  page: number;
  pageCount: number;
  total: number;
  perPage: number;
  onPageChange: (page: number) => void;
  onPerPageChange: (perPage: number) => void;
  className?: string;
}

export function Pagination({ page, pageCount, total, perPage, onPageChange, onPerPageChange, className }: PaginationProps) {
  const from = (page - 1) * perPage + 1;
  const to = Math.min(page * perPage, total);
  const getPageNumbers = (): (number | string)[] => {
    if (pageCount <= 7) {
      return Array.from({ length: pageCount }, (_, i) => i + 1);
    }
    const pages: (number | string)[] = [1];
    if (page > 3) pages.push('...');
    for (let i = Math.max(2, page - 1); i <= Math.min(pageCount - 1, page + 1); i++) {
      pages.push(i);
    }
    if (page < pageCount - 2) pages.push('...');
    pages.push(pageCount);
    return pages;
  };

  return (
    <div className={cn('flex items-center justify-between px-4 py-3 border-t border-slate-200 bg-slate-50 rounded-b-lg', className)}>
      <span className="text-sm text-slate-500">
        Показано {from}–{to} из {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
          className="p-1.5 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Предыдущая страница"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        {getPageNumbers().map((p, index) =>
          typeof p === 'number' ? (
            <button
              key={index}
              onClick={() => onPageChange(p)}
              className={cn(
                'px-3 py-1.5 text-sm rounded-md transition-colors',
                p === page
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-600 hover:bg-slate-100'
              )}
            >
              {p}
            </button>
          ) : (
            <span key={index} className="px-1.5 text-sm text-slate-400">
              {p}
            </span>
          )
        )}
        <button
          onClick={() => onPageChange(Math.min(pageCount, page + 1))}
          disabled={page >= pageCount}
          className="p-1.5 rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Следующая страница"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <select
          value={perPage}
          onChange={(e) => onPerPageChange(Number(e.target.value))}
          className="ml-2 text-sm border border-slate-200 rounded-md px-2 py-1.5 bg-white"
        >
          {[20, 50, 100].map((size) => (
            <option key={size} value={size}>
              {size} / стр
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}