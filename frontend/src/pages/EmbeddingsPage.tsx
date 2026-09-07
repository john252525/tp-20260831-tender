import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Dna, Search, Loader2, GitCompare, Sparkles } from 'lucide-react';
import { embeddingsApi } from '../api/embeddings';
import { PageHeader } from '../components/common/PageHeader';
import { StatusBadge } from '../components/common/StatusBadge';
import { cn } from '../lib/utils';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';

export function EmbeddingsPage() {
  const [generateText, setGenerateText] = useState('');
  const generateMutation = useMutation({
    mutationFn: (text: string) => embeddingsApi.generate({ text }),
    onSuccess: (data) => toast.success(`Эмбеддинг сгенерирован (${data.dimensions} измерений, ${data.tokens_used} токенов)`),
    onError: () => toast.error('Не удалось сгенерировать'),
  });

  const [similarityText1, setSimilarityText1] = useState('');
  const [similarityText2, setSimilarityText2] = useState('');
  const similarityMutation = useMutation({
    mutationFn: (data: { text1: string; text2: string }) => embeddingsApi.similarity(data),
    onSuccess: () => toast.success('Сравнение выполнено'),
    onError: () => toast.error('Не удалось сравнить'),
  });

  const [searchText, setSearchText] = useState('');
  const [searchType, setSearchType] = useState<'tender' | 'category'>('tender');
  const [searchTopK, setSearchTopK] = useState('10');
  const [searchMinSimilarity, setSearchMinSimilarity] = useState('0.6');
  const searchMutation = useMutation({
    mutationFn: (data: any) => embeddingsApi.searchSimilar(data),
    onSuccess: () => toast.success('Поиск выполнен'),
    onError: () => toast.error('Не удалось выполнить поиск'),
  });

  const similarityResult = similarityMutation.data;
  const similarityValue = similarityResult?.cosine_similarity;
  const getSimilarityColor = (value: number | undefined): string => {
    if (value === undefined) return 'text-slate-500';
    if (value >= 0.8) return 'text-green-600';
    if (value >= 0.6) return 'text-yellow-600';
    if (value >= 0.4) return 'text-orange-600';
    return 'text-red-600';
  };
  const searchResults = searchMutation.data || [];

  return (
    <div>
      <PageHeader title="Эмбеддинги" description="Отладка семантического поиска" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2 mb-4"><div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center"><Sparkles className="h-4 w-4 text-purple-700" /></div><h3 className="text-base font-semibold text-slate-900">Генерация</h3></div>
          <div className="space-y-3">
            <div>
              <Label>Текст</Label>
              <Textarea value={generateText} onChange={(e) => setGenerateText(e.target.value)} placeholder="Поставка ноутбуков HP ProBook" rows={5} className="mt-1" />
            </div>
            <Button onClick={() => generateMutation.mutate(generateText)} disabled={!generateText.trim() || generateMutation.isPending} className="w-full">
              {generateMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Sparkles className="h-4 w-4 mr-2" />}
              Сгенерировать
            </Button>
            {generateMutation.data && (
              <div className="bg-slate-50 rounded-lg p-3 text-xs">
                <p className="text-slate-500 mb-1">Размерность: {generateMutation.data.dimensions}</p>
                <p className="text-slate-500 mb-1">Токенов: {generateMutation.data.tokens_used}</p>
                <p className="text-slate-500 mb-1">Preview:</p>
                <code className="block break-all text-slate-700">[{generateMutation.data.embedding_preview.slice(0, 10).map((v: number) => v.toFixed(4)).join(', ')}...]</code>
              </div>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2 mb-4"><div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center"><GitCompare className="h-4 w-4 text-blue-700" /></div><h3 className="text-base font-semibold text-slate-900">Сравнение</h3></div>
          <div className="space-y-3">
            <div><Label>Текст 1</Label><Textarea value={similarityText1} onChange={(e) => setSimilarityText1(e.target.value)} placeholder="Поставка ноутбуков HP" rows={3} className="mt-1" /></div>
            <div><Label>Текст 2</Label><Textarea value={similarityText2} onChange={(e) => setSimilarityText2(e.target.value)} placeholder="Закупка портативных компьютеров" rows={3} className="mt-1" /></div>
            <Button onClick={() => similarityMutation.mutate({ text1: similarityText1, text2: similarityText2 })} disabled={!similarityText1.trim() || !similarityText2.trim() || similarityMutation.isPending} className="w-full">
              {similarityMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <GitCompare className="h-4 w-4 mr-2" />}
              Сравнить
            </Button>
            {similarityResult && (
              <div className="text-center py-4">
                <p className={cn('text-4xl font-bold', getSimilarityColor(similarityValue))}>{similarityValue?.toFixed(4)}</p>
                <p className="text-xs text-slate-400 mt-2">Косинусное сходство</p>
                {similarityValue !== undefined && similarityValue >= 0.8 && <p className="text-xs text-green-600 mt-1">✅ Очень похожие тексты</p>}
                {similarityValue !== undefined && similarityValue >= 0.6 && similarityValue < 0.8 && <p className="text-xs text-yellow-600 mt-1">⚠️ Умеренное сходство</p>}
                {similarityValue !== undefined && similarityValue < 0.6 && <p className="text-xs text-red-600 mt-1">❌ Разные тексты</p>}
              </div>
            )}
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center gap-2 mb-4"><div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center"><Search className="h-4 w-4 text-green-700" /></div><h3 className="text-base font-semibold text-slate-900">Поиск похожих</h3></div>
          <div className="space-y-3">
            <div><Label>Текст</Label><Textarea value={searchText} onChange={(e) => setSearchText(e.target.value)} placeholder="Ноутбуки HP оптом" rows={3} className="mt-1" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><Label>Сущность</Label><Select value={searchType} onValueChange={(value: 'tender' | 'category') => setSearchType(value)}><SelectTrigger className="mt-1"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="tender">Тендер</SelectItem><SelectItem value="category">Категория</SelectItem></SelectContent></Select></div>
              <div><Label>Top-K</Label><Input type="number" min={1} max={50} value={searchTopK} onChange={(e) => setSearchTopK(e.target.value)} className="mt-1" /></div>
            </div>
            <div><Label>Мин. сходство</Label><Input type="number" min={0} max={1} step={0.05} value={searchMinSimilarity} onChange={(e) => setSearchMinSimilarity(e.target.value)} className="mt-1" /></div>
            <Button onClick={() => searchMutation.mutate({ text: searchText, entity_type: searchType, top_k: Number(searchTopK), min_similarity: Number(searchMinSimilarity) })} disabled={!searchText.trim() || searchMutation.isPending} className="w-full">
              {searchMutation.isPending ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Search className="h-4 w-4 mr-2" />}
              Найти
            </Button>
            {searchResults.length > 0 && (
              <div className="max-h-[200px] overflow-y-auto space-y-1">
                {searchResults.map((result: any, index: number) => (
                  <div key={result.id || index} className="rounded-md bg-slate-50 p-2">
                    <p className="text-xs font-medium text-slate-900 truncate">{result.title || result.name || result.id}</p>
                    <p className="text-xs text-slate-500">Сходство: <span className="font-semibold">{result.similarity?.toFixed(3)}</span>{result.status && <span className="ml-2"><StatusBadge status={result.status} size="sm" /></span>}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}