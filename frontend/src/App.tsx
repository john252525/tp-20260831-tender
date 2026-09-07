import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { useAuth } from './hooks/useAuth';
import { AppShell } from './components/layout/AppShell';

const AuthPage = lazy(() => import('./pages/AuthPage').then(m => ({ default: m.AuthPage })));
const PipelinePage = lazy(() => import('./pages/PipelinePage').then(m => ({ default: m.PipelinePage })));
const TendersPage = lazy(() => import('./pages/TendersPage').then(m => ({ default: m.TendersPage })));
const TenderDetailPage = lazy(() => import('./pages/TenderDetailPage').then(m => ({ default: m.TenderDetailPage })));
const SuppliersPage = lazy(() => import('./pages/SuppliersPage').then(m => ({ default: m.SuppliersPage })));
const SupplierDetailPage = lazy(() => import('./pages/SupplierDetailPage').then(m => ({ default: m.SupplierDetailPage })));
const DecisionsPage = lazy(() => import('./pages/DecisionsPage').then(m => ({ default: m.DecisionsPage })));
const TasksPage = lazy(() => import('./pages/TasksPage').then(m => ({ default: m.TasksPage })));
const AutomationPage = lazy(() => import('./pages/AutomationPage').then(m => ({ default: m.AutomationPage })));
const CategoriesPage = lazy(() => import('./pages/CategoriesPage').then(m => ({ default: m.CategoriesPage })));
const SourcesPage = lazy(() => import('./pages/SourcesPage').then(m => ({ default: m.SourcesPage })));
const TemplatesPage = lazy(() => import('./pages/TemplatesPage').then(m => ({ default: m.TemplatesPage })));
const ScoringPage = lazy(() => import('./pages/ScoringPage').then(m => ({ default: m.ScoringPage })));
const NegotiationSettingsPage = lazy(() => import('./pages/NegotiationSettingsPage').then(m => ({ default: m.NegotiationSettingsPage })));
const WebhooksPage = lazy(() => import('./pages/WebhooksPage').then(m => ({ default: m.WebhooksPage })));
const CompanySettingsPage = lazy(() => import('./pages/CompanySettingsPage').then(m => ({ default: m.CompanySettingsPage })));
const TokensPage = lazy(() => import('./pages/TokensPage').then(m => ({ default: m.TokensPage })));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage').then(m => ({ default: m.AnalyticsPage })));
const EmbeddingsPage = lazy(() => import('./pages/EmbeddingsPage').then(m => ({ default: m.EmbeddingsPage })));
const LogsPage = lazy(() => import('./pages/LogsPage').then(m => ({ default: m.LogsPage })));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage').then(m => ({ default: m.NotFoundPage })));

function PageLoader() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );
}

function ProtectedLayout() {
  const { token, isLoading } = useAuth();
  if (isLoading) return <PageLoader />;
  if (!token) return <Navigate to="/auth" replace />;
  return (
    <AppShell>
      <Suspense fallback={<PageLoader />}>
        <Outlet />
      </Suspense>
    </AppShell>
  );
}

const router = createBrowserRouter([
  {
    path: '/auth',
    element: (
      <Suspense fallback={<PageLoader />}>
        <AuthPage />
      </Suspense>
    ),
  },
  {
    path: '/',
    element: <ProtectedLayout />,
    children: [
      { index: true, element: <PipelinePage /> },
      { path: 'tenders', element: <TendersPage /> },
      { path: 'tenders/:tenderId', element: <TenderDetailPage /> },
      { path: 'suppliers', element: <SuppliersPage /> },
      { path: 'suppliers/:supplierId', element: <SupplierDetailPage /> },
      { path: 'decisions', element: <DecisionsPage /> },
      { path: 'tasks', element: <TasksPage /> },
      { path: 'automation', element: <AutomationPage /> },
      { path: 'automation/categories', element: <CategoriesPage /> },
      { path: 'automation/sources', element: <SourcesPage /> },
      { path: 'automation/templates', element: <TemplatesPage /> },
      { path: 'automation/scoring', element: <ScoringPage /> },
      { path: 'automation/negotiation', element: <NegotiationSettingsPage /> },
      { path: 'automation/webhooks', element: <WebhooksPage /> },
      { path: 'settings/company', element: <CompanySettingsPage /> },
      { path: 'settings/tokens', element: <TokensPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'debug/embeddings', element: <EmbeddingsPage /> },
      { path: 'debug/logs', element: <LogsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);

export function App() {
  return <RouterProvider router={router} />;
}