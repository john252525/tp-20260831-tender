import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, KeyRound, Building2, AlertCircle } from 'lucide-react';
import { apiClient } from '../api/client';
import { cn } from '../lib/utils';

type AuthState = 'idle' | 'loading' | 'error';

export function AuthPage() {
  const [token, setToken] = useState('');
  const [state, setState] = useState<AuthState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmedToken = token.trim();
    if (!trimmedToken) return;

    setState('loading');
    setErrorMessage('');

    try {
      await apiClient.get('/health', {
        headers: { 'X-Api-Token': trimmedToken },
      });
      localStorage.setItem('api_token', trimmedToken);
      toast.success('Добро пожаловать!');
      navigate('/', { replace: true });
    } catch (error: any) {
      setState('error');
      if (error.response?.status === 401) {
        setErrorMessage('Неверный токен. Проверьте и попробуйте снова.');
      } else if (error.code === 'ECONNABORTED' || !error.response) {
        setErrorMessage('Сервер недоступен. Проверьте подключение и попробуйте снова.');
      } else {
        setErrorMessage('Произошла ошибка. Попробуйте снова.');
      }
    }
  };

  const isDisabled = !token.trim() || state === 'loading';

  return (
    <div className="min-h-screen flex items-center justify-center bg-white px-4">
      <div className="w-full max-w-sm">
        {/* Логотип и заголовок */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mb-6">
            <Building2 className="w-8 h-8 text-slate-400" />
          </div>
          <h1 className="text-2xl font-semibold text-slate-900 mb-2">
            Тендерный конвейер
          </h1>
          <p className="text-sm text-slate-500 text-center">
            Введите API-токен для доступа к системе
          </p>
        </div>

        {/* Ошибка */}
        {state === 'error' && (
          <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-3 mb-4">
            <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{errorMessage}</p>
          </div>
        )}

        {/* Форма */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              type="password"
              value={token}
              onChange={(e) => {
                setToken(e.target.value);
                if (state === 'error') setState('idle');
              }}
              placeholder="Введите токен"
              className={cn(
                'w-full h-9 pl-10 pr-4 border rounded-lg text-sm focus:outline-none focus:ring-2 transition-colors',
                state === 'error'
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-100'
                  : 'border-slate-200 focus:border-blue-500 focus:ring-blue-100'
              )}
              disabled={state === 'loading'}
              autoFocus
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <button
            type="submit"
            disabled={isDisabled}
            className={cn(
              'w-full h-9 rounded-lg text-sm font-medium transition-colors inline-flex items-center justify-center gap-2',
              isDisabled
                ? 'bg-slate-300 text-white cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            )}
          >
            {state === 'loading' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Проверка...
              </>
            ) : (
              'Войти'
            )}
          </button>
        </form>

        {/* Подсказка */}
        <p className="text-xs text-slate-400 text-center mt-8">
          Токен выдаётся администратором системы
        </p>
      </div>
    </div>
  );
}