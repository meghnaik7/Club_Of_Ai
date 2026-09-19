import api from '../lib/axios';

export type Announcement = {
  id: number;
  title: string;
  content: string;
  event_id?: number;
  target_audience?: string;
  status: string;
  variants?: string;
  created_by?: number;
  created_at: string;
  updated_at: string;
}

export type AnnouncementCreate = {
  title: string;
  content: string;
  event_id?: number;
  target_audience?: string;
  variants?: string;
}

export type AnnouncementUpdate = {
  title?: string;
  content?: string;
  target_audience?: string;
  status?: string;
  variants?: string;
}

export type GenerateRequest = {
  event_id: number;
  tone?: string;
  target_audience?: string;
  key_highlights?: string[];
}

export type GenerateResponse = {
  title: string;
  content: string;
  event_id: number;
  event_title: string;
  event_date?: string;
  venue?: string;
}

export type VariantsResponse = {
  announcement_id?: number;
  whatsapp: string;
  email: { subject: string; body: string };
  instagram: { caption: string; hashtags: string[] };
}

const AnnouncementsService = {
  list: (event_id?: number) =>
    api.get<Announcement[]>('/announcements', { params: event_id ? { event_id } : undefined }).then(r => r.data),
  get: (id: number) => api.get<Announcement>(`/announcements/${id}`).then(r => r.data),
  create: (data: AnnouncementCreate) => api.post<Announcement>('/announcements', data).then(r => r.data),
  update: (id: number, data: AnnouncementUpdate) => api.put<Announcement>(`/announcements/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/announcements/${id}`).then(r => r.data),
  generate: (data: GenerateRequest) =>
    api.post<GenerateResponse>('/announcements/generate', data).then(r => r.data),
  generateVariants: (id: number) =>
    api.post<VariantsResponse>(`/announcements/${id}/variants`).then(r => r.data),
};

export default AnnouncementsService;
