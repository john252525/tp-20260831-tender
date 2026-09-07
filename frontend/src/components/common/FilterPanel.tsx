import { useState } from 'react';
import { ChevronDown, ChevronUp, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';

interface FilterPanelProps {
  children: React.ReactNode;
  activeFilterCount?: number;
  onReset?: () => void;
  className?: string;
  defaultOpen?: boolean;
}

export function FilterPanel({ children, activeFilterCount = 0, onReset, className, defaultOpen = false }: FilterPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={cn('rounded-lg border border-slate-200 bg-white', className)}>
      <div className="flex items-center justify-between p-3 border-b border-slate-100">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          Фильтры
          {activeFilterCount > 0 && (
            <span className="bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 text-xs font-semibold">
              {activeFilterCount}
            </span>
          )}
        </button>
        {activeFilterCount > 0 && onReset && (
          <Button variant="ghost" size="sm" onClick={onReset} className="text-slate-500 hover:text-slate-700">
            <X className="h-3.5 w-3.5 mr-1" />
            Сбросить
          </Button>
        )}
      </div>
      {isOpen && <div className="p-3">{children}</div>}
    </div>
  );
}