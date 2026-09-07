import { apiClient, extractData } from './client';

export interface FileInfo {
  id: string;
  filename: string;
  file_size_bytes: number | null;
  mime_type: string;
  storage_path: string;
  uploaded_at: string;
  download_url: string | null;
}

export const filesApi = {
  async upload(file: File, entityType: string, entityId: string): Promise<FileInfo> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('entity_type', entityType);
    formData.append('entity_id', entityId);
    const response = await apiClient.post('/files/upload', formData);
    return extractData(response);
  },
  async download(id: string): Promise<Blob> {
    const response = await apiClient.get(`/files/${id}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },
  async delete(id: string): Promise<any> {
    const response = await apiClient.delete(`/files/${id}`);
    return extractData(response);
  },
};