import { apiClient, extractData } from './client';

export const embeddingsApi = {
  async generate(data: { text: string; model?: string }): Promise<{
    dimensions: number;
    tokens_used: number;
    embedding_preview: number[];
  }> {
    const response = await apiClient.post('/embeddings/generate', data);
    return extractData(response);
  },
  async similarity(data: { text1: string; text2: string }): Promise<{
    cosine_similarity: number;
    model: string;
  }> {
    const response = await apiClient.post('/embeddings/similarity', data);
    return extractData(response);
  },
  async searchSimilar(data: {
    text: string;
    entity_type: 'tender' | 'category';
    top_k?: number;
    min_similarity?: number;
    filters?: any;
  }): Promise<any[]> {
    const response = await apiClient.post('/embeddings/search-similar', data);
    return extractData(response);
  },
};