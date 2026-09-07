import { LogOut, Menu } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../ui/button';

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const { logout } = useAuth();

  return (
    <header className="sticky top-0 z-20 h-14 border-b border-slate-200 bg-white px-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="lg:hidden p-1.5 rounded-md hover:bg-slate-100 text-slate-600"
          aria-label="Открыть меню"
        >
          <Menu className="h-5 w-5" />
        </button>
        <span className="font-semibold text-slate-900">Тендерный конвейер</span>
      </div>
      <Button variant="ghost" size="sm" onClick={logout} className="text-slate-600">
        <LogOut className="h-4 w-4 mr-2" aria-hidden="true" />
        Выйти
      </Button>
    </header>
  );
}