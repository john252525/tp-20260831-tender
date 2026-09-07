import axios from 'axios';

const getApiBaseUrl = (): string | undefined => {
  // Для Vite (браузер)
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  // Для Jest (Node)
  if (typeof process !== 'undefined' && process.env) {
    return process.env.VITE_API_BASE_URL;
  }
  return undefined;
};

const API_BASE_URL = getApiBaseUrl() || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: токен + идемпотентность
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('api_token');
  if (token) {
    config.headers['X-Api-Token'] = token;
  }
  if (['post', 'put', 'patch', 'delete'].includes(config.method?.toLowerCase() ?? '')) {
    config.headers['Idempotency-Key'] =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`;
  }
  return config;
});

// Response interceptor: обработка 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('api_token');
      window.dispatchEvent(new CustomEvent('auth:expired'));
    }
    return Promise.reject(error);
  },
);

// Вспомогательная функция извлечения данных
export function extractData<T>(response: { data: { success: boolean; data: T } }): T {
  if (!response.data.success) {
    throw new Error('API вернул success: false');
  }
  return response.data.data;
}

// Вспомогательная функция извлечения ошибки
export function extractError(error: any): { code: string; message: string; details?: any } {
  return (
    error.response?.data?.error || {
      code: 'UNKNOWN_ERROR',
      message: error.message || 'Произошла неизвестная ошибка',
    }
  );
}