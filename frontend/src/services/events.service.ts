import api from '../lib/axios';

export type Event = {
  id: number;
  title: string;
  description?: string;
  date: string;
  venue?: string;
  status: string;
  budget?: number;
  budget_spent?: number;
  expected_attendance?: number;
  created_by?: number;
}

export type EventCreate = {
  title: string;
  description?: string;
  date: string;
  venue?: string;
  status?: string;
  budget?: number;
  budget_spent?: number;
  expected_attendance?: number;
}

export type EventUpdate = Partial<EventCreate>;

const EventsService = {
  list: () => api.get<Event[]>('/events').then(r => r.data),
  get: (id: number) => api.get<Event>(`/events/${id}`).then(r => r.data),
  create: (data: EventCreate) => api.post<Event>('/events', data).then(r => r.data),
  update: (id: number, data: EventUpdate) => api.put<Event>(`/events/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/events/${id}`).then(r => r.data),
};

export default EventsService;
