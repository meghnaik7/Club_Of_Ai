import api from '../lib/axios';

export interface DocumentItem {
  id: string;
  name: string;
  filename: string;
  file_type: string;
  file_size: number;
  category: string;
  event_id?: string;
  uploader: string;
  chunk_count: number;
  created_at: string;
}

export interface RAGSource {
  source: string;
  page_number?: number;
  section_name?: string;
}

export interface RAGHistoryItem {
  id: number;
  question: string;
  answer: string;
  citations: Array<{ source?: string; page?: number; section?: string }>;
  status: string;
  created_at: string;
}

export interface RAGQueryResponse {
  answer: string;
  confidence: number;
  sources: RAGSource[];
  retrieved_chunks_count: number;
  used_web_search: boolean;
}

const DocumentsService = {
  listDocuments: (params?: { event_id?: string; category?: string; search?: string }) =>
    api.get<{ items: DocumentItem[]; total: number }>('/documents/', { params }).then(r => r.data),

  uploadDocument: (formData: FormData) =>
    api.post<DocumentItem>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data),

  deleteDocument: (documentId: string) =>
    api.delete<{ ok: boolean; message: string }>(`/documents/${documentId}`).then(r => r.data),

  queryRAG: (data: { query: string; event_id?: string; category?: string; top_k?: number }) =>
    api.post<RAGQueryResponse>('/documents/rag/query', data).then(r => r.data),

  getRAGHistory: (eventId?: string) =>
    api.get<{ items: RAGHistoryItem[]; total: number }>('/documents/rag/history', {
      params: eventId ? { event_id: eventId } : {}
    }).then(r => r.data),

  clearRAGHistory: (eventId?: string) =>
    api.delete<{ ok: boolean; deleted_count: number }>('/documents/rag/history', {
      params: eventId ? { event_id: eventId } : {}
    }).then(r => r.data),
};

export default DocumentsService;
