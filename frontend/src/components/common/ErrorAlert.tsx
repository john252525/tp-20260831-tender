import { AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '../../lib/utils';

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorAlert({ message, onRetry, className }: ErrorAlertProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-4',
        className
      )}
      role="alert"
    >
      <div className="flex items-center gap-3">
        <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" aria-hidden="true" />
        <p className="text-sm text-red-700">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 rounded-md border border-red-200 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Повторить
        </button>
      )}
    </div>
  );
}