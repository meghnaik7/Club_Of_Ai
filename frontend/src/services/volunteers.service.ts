import api from '../lib/axios';

export type UserInfo = {
  id: number;
  full_name: string;
  email: string;
}

export type Volunteer = {
  id: number;
  user_id: number;
  skills?: string;
  availability?: string;
  status: string;
  active_task_count?: number;
  load_indicator?: string;
  user?: UserInfo;
}

export type VolunteerCreate = {
  user_id: number;
  skills?: string;
  availability?: string;
  status?: string;
}

export type VolunteerUpdate = Partial<Omit<VolunteerCreate, 'user_id'>>;

const VolunteersService = {
  list: () => api.get<Volunteer[]>('/volunteers').then(r => r.data),
  get: (id: number) => api.get<Volunteer>(`/volunteers/${id}`).then(r => r.data),
  getTasks: (id: number) => api.get<any[]>(`/volunteers/${id}/tasks`).then(r => r.data),
  create: (data: VolunteerCreate) => api.post<Volunteer>('/volunteers', data).then(r => r.data),
  update: (id: number, data: VolunteerUpdate) => api.put<Volunteer>(`/volunteers/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/volunteers/${id}`).then(r => r.data),
};

export default VolunteersService;
