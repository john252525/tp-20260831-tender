import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  FolderTree,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  Dna,
  ChevronRight,
  ChevronDown,
  Upload,
} from 'lucide-react';
import { categoriesApi, type Category } from '../api/categories';
import { LoadingSkeleton } from '../components/common/LoadingSkeleton';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { PageHeader } from '../components/common/PageHeader';
import { cn } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

function CategoryTreeNode({ category, selectedId, onSelect, level = 0 }: {
  category: any;
  selectedId: string | null;
  onSelect: (id: string) => void;
  level?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const children = category.children || [];
  return (
    <div>
      <button
        onClick={() => onSelect(category.id)}
        className={cn(
          'w-full flex items-center gap-2 px-3 py-2 text-sm rounded-md transition-colors text-left',
          selectedId === category.id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-slate-700 hover:bg-slate-100'
        )}
        style={{ paddingLeft: `${12 + level * 20}px` }}
      >
        {children.length > 0 ? (
          <span
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
            className="text-slate-400 hover:text-slate-600"
          >
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </span>
        ) : (
          <span className="w-4" />
        )}
        <FolderTree className="h-4 w-4 text-slate-400 flex-shrink-0" aria-hidden="true" />
        <span className="flex-1 truncate">{category.name}</span>
        {!category.is_active && (
          <span className="text-[10px] bg-slate-100 text-slate-500 rounded-full px-1.5 py-0.5">неактивна</span>
        )}
      </button>
      {expanded && children.length > 0 && (
        <div>
          {children.map((child: any) => (
            <CategoryTreeNode key={child.id} category={child} selectedId={selectedId} onSelect={onSelect} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function CategoryForm({ category, allCategories, onSave, onDeactivate, onReEmbed, isSaving, isDeactivating, isReEmbedding }: {
  category: Category | null;
  allCategories: Category[];
  onSave: (data: any) => void;
  onDeactivate: () => void;
  onReEmbed: () => void;
  isSaving: boolean;
  isDeactivating: boolean;
  isReEmbedding: boolean;
}) {
  const [form, setForm] = useState({
    name: category?.name || '',
    description: category?.description || '',
    keywords: category?.keywords?.join(', ') || '',
    parent_id: category?.parent_id || '',
  });

  const handleSubmit = () => {
    if (!form.name.trim() || !form.description.trim()) {
      toast.error('Название и описание обязательны');
      return;
    }
    onSave({
      name: form.name.trim(),
      description: form.description.trim(),
      keywords: form.keywords ? form.keywords.split(',').map((k: string) => k.trim()).filter(Boolean) : [],
      parent_id: form.parent_id || null,
    });
  };

  return (
    <div className="space-y-4">
      <div>
        <Label>Название *</Label>
        <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Оргтехника" />
      </div>
      <div>
        <Label>Описание * (влияет на качество семантического поиска)</Label>
        <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Компьютеры, ноутбуки, мониторы..." rows={4} />
        <p className="text-xs text-slate-400 mt-1">Описывайте максимально подробно — это влияет на точность поиска тендеров</p>
      </div>
      <div>
        <Label>Ключевые слова (через запятую)</Label>
        <Input value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} placeholder="ПК, ноутбук, МФУ, картридж" />
      </div>
      <div>
        <Label>Родительская категория</Label>
        <Select value={form.parent_id || 'none'} onValueChange={(value) => setForm({ ...form, parent_id: value === 'none' ? '' : value })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">Нет (корневая)</SelectItem>
            {allCategories.filter((c) => c.id !== category?.id).map((c) => (
              <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex gap-2 pt-2">
        <Button onClick={handleSubmit} disabled={isSaving}>
          {isSaving ? 'Сохранение...' : '💾 Сохранить'}
        </Button>
        {category?.id && (
          <>
            <Button variant="outline" onClick={onReEmbed} disabled={isReEmbedding}>
              {isReEmbedding ? <RefreshCw className="h-4 w-4 mr-1.5 animate-spin" /> : <Dna className="h-4 w-4 mr-1.5" />}
              Перегенерировать эмбеддинг
            </Button>
            <Button variant="outline" onClick={onDeactivate} disabled={isDeactivating}>
              <Trash2 className="h-4 w-4 mr-1.5 text-red-500" />
              Деактивировать
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

function ImportModal({ open, onOpenChange, onImport, isLoading }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImport: (text: string) => void;
  isLoading: boolean;
}) {
  const [jsonText, setJsonText] = useState('');
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Импорт категорий</DialogTitle>
          <DialogDescription>Вставьте JSON-массив с категориями</DialogDescription>
        </DialogHeader>
        <Textarea
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          placeholder={'[\n  {\n    "name": "Оргтехника",\n    "description": "Компьютеры, ноутбуки...",\n    "keywords": ["ПК", "ноутбук"]\n  }\n]'}
          rows={10}
          className="font-mono text-xs"
          aria-label="JSON категорий"
        />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>Отмена</Button>
          <Button onClick={() => onImport(jsonText)} disabled={isLoading}>
            {isLoading ? 'Импорт...' : 'Импортировать'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(false);

  const categoriesQuery = useQuery({
    queryKey: ['categories', 'all'],
    queryFn: () => categoriesApi.list({ per_page: 100 }),
  });

  const saveMutation = useMutation({
    mutationFn: ({ id, data }: { id?: string; data: any }) =>
      id ? categoriesApi.put(id, data) : categoriesApi.create(data),
    onSuccess: () => {
      toast.success('Категория сохранена');
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
    onError: () => toast.error('Не удалось сохранить'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.delete(id),
    onSuccess: () => {
      toast.success('Категория деактивирована');
      setConfirmDeactivate(false);
      setSelectedId(null);
      queryClient.invalidateQueries({ queryKey: ['categories'] });
    },
    onError: () => toast.error('Не удалось деактивировать'),
  });

  const reEmbedMutation = useMutation({
    mutationFn: (id: string) => categoriesApi.reEmbed(id),
    onSuccess: () => toast.success('Перегенерация запущена'),
    onError: () => toast.error('Не удалось запустить'),
  });

  const importMutation = useMutation({
    mutationFn: (text: string) => categoriesApi.bulkImport(JSON.parse(text)),
    onSuccess: (data) => {
      toast.success(`Импорт запущен (задача: ${data.task_id?.slice(0, 8)}...)`);
      setShowImport(false);
    },
    onError: () => toast.error('Не удалось импортировать'),
  });

  const allCategories = categoriesQuery.data || [];
  const selectedCategory = allCategories.find((c) => c.id === selectedId) || null;

  const filteredCategories = useMemo(() => {
    if (!searchText.trim()) return allCategories;
    return allCategories.filter(
      (c) =>
        c.name.toLowerCase().includes(searchText.toLowerCase()) ||
        (c.keywords || []).some((k: string) => k.toLowerCase().includes(searchText.toLowerCase()))
    );
  }, [allCategories, searchText]);

  const buildTree = (categories: Category[]): any[] => {
    const map = new Map<string, any>();
    categories.forEach((c) => map.set(c.id, { ...c, children: [] }));
    const roots: any[] = [];
    map.forEach((node) => {
      if (node.parent_id && map.has(node.parent_id)) {
        map.get(node.parent_id)!.children.push(node);
      } else {
        roots.push(node);
      }
    });
    return roots;
  };

  const tree = buildTree(filteredCategories);

  return (
    <div>
      <PageHeader
        title="Категории"
        description="Профильные категории для семантического поиска тендеров"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
              <Upload className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Импорт
            </Button>
            <Button variant="outline" size="sm" onClick={() => categoriesQuery.refetch()}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Обновить
            </Button>
            <Button size="sm" onClick={() => setSelectedId(null)}>
              <Plus className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" />
              Создать
            </Button>
          </>
        }
      />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="p-3 border-b border-slate-200">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input placeholder="Поиск категорий..." value={searchText} onChange={(e) => setSearchText(e.target.value)} className="pl-9" />
            </div>
          </div>
          <div className="p-2 max-h-[600px] overflow-y-auto">
            {categoriesQuery.isLoading ? (
              <LoadingSkeleton rows={5} cols={1} type="card" />
            ) : categoriesQuery.isError ? (
              <ErrorAlert message="Не удалось загрузить категории" onRetry={() => categoriesQuery.refetch()} />
            ) : tree.length === 0 ? (
              <EmptyState icon={FolderTree} title="Категорий нет" description="Создайте первую категорию для поиска тендеров" actionLabel="Создать категорию" onAction={() => setSelectedId(null)} />
            ) : (
              tree.map((node) => (
                <CategoryTreeNode key={node.id} category={node} selectedId={selectedId} onSelect={setSelectedId} />
              ))
            )}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h3 className="text-base font-semibold text-slate-900 mb-4">
            {selectedCategory ? 'Редактирование' : 'Новая категория'}
          </h3>
          <CategoryForm
            category={selectedCategory}
            allCategories={allCategories}
            onSave={(data) => {
              if (selectedCategory) saveMutation.mutate({ id: selectedCategory.id, data });
              else saveMutation.mutate({ data });
            }}
            onDeactivate={() => setConfirmDeactivate(true)}
            onReEmbed={() => selectedCategory && reEmbedMutation.mutate(selectedCategory.id)}
            isSaving={saveMutation.isPending}
            isDeactivating={deleteMutation.isPending}
            isReEmbedding={reEmbedMutation.isPending}
          />
        </div>
      </div>
      <ImportModal
        open={showImport}
        onOpenChange={setShowImport}
        onImport={(text) => {
          try {
            JSON.parse(text);
            importMutation.mutate(text);
          } catch {
            toast.error('Неверный JSON');
          }
        }}
        isLoading={importMutation.isPending}
      />
      <ConfirmDialog
        open={confirmDeactivate}
        onOpenChange={setConfirmDeactivate}
        title="Деактивировать категорию"
        description={selectedCategory ? `Категория «${selectedCategory.name}» будет деактивирована.` : ''}
        confirmLabel="Деактивировать"
        variant="destructive"
        isLoading={deleteMutation.isPending}
        onConfirm={() => selectedCategory && deleteMutation.mutate(selectedCategory.id)}
      />
    </div>
  );
}