import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Building2,
  CheckSquare,
  Activity,
  Bot,
  FolderTree,
  RadioTower,
  Mail,
  Gauge,
  MessagesSquare,
  Webhook,
  Building,
  KeyRound,
  BarChart3,
  Dna,
  ScrollText,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../lib/utils';

interface MenuItem {
  to: string;
  label: string;
  icon: LucideIcon;
  indent?: boolean;
}

const menuItems: MenuItem[] = [
  { to: '/', label: 'Конвейер', icon: LayoutDashboard },
  { to: '/tenders', label: 'Тендеры', icon: FileText },
  { to: '/suppliers', label: 'Поставщики', icon: Building2 },
  { to: '/decisions', label: 'Решения', icon: CheckSquare },
  { to: '/tasks', label: 'Задачи', icon: Activity },
  { to: '/automation', label: 'Автопилот', icon: Bot },
  { to: '/automation/categories', label: 'Категории', icon: FolderTree, indent: true },
  { to: '/automation/sources', label: 'Источники', icon: RadioTower, indent: true },
  { to: '/automation/templates', label: 'Шаблоны писем', icon: Mail, indent: true },
  { to: '/automation/scoring', label: 'Скоринг', icon: Gauge, indent: true },
  { to: '/automation/negotiation', label: 'Переговоры', icon: MessagesSquare, indent: true },
  { to: '/automation/webhooks', label: 'Вебхуки', icon: Webhook, indent: true },
  { to: '/settings/company', label: 'Компания', icon: Building },
  { to: '/settings/tokens', label: 'API-токены', icon: KeyRound },
  { to: '/analytics', label: 'Аналитика', icon: BarChart3 },
  { to: '/debug/embeddings', label: 'Эмбеддинги', icon: Dna },
  { to: '/debug/logs', label: 'Журнал', icon: ScrollText },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 w-60 bg-white border-r border-slate-200 transform transition-transform duration-200 lg:translate-x-0 lg:static lg:inset-auto',
        open ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      <div className="h-full flex flex-col overflow-y-auto py-4">
        <nav className="px-2 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isAutomationParent = item.to === '/automation';
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/' || isAutomationParent}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                    item.indent && 'ml-4'
                  )
                }
              >
                <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}