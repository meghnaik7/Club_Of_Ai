import api from '../lib/axios';

export type TaskStatus = 'TODO' | 'IN_PROGRESS' | 'DONE' | 'BLOCKED';
export type TaskPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
export type TaskPhase = 'PLANNING' | 'EXECUTION' | 'POST_EVENT';

export type TaskAssignment = {
  id: number;
  task_id: number;
  volunteer_id: number;
}

export type Task = {
  id: number;
  event_id: number;
  title: string;
  description?: string;
  status: TaskStatus;
  priority: TaskPriority;
  phase?: TaskPhase;
  start_date?: string;
  due_date?: string;
  parent_id?: number;
  assignments: TaskAssignment[];
  dependencies_out: any[];
  dependencies_in: any[];
  comments: any[];
}

export type TaskCreate = {
  event_id: number;
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
  phase?: TaskPhase;
  start_date?: string;
  due_date?: string;
  parent_id?: number;
  owner_ids?: number[];
}

export type TaskUpdate = Partial<Omit<TaskCreate, 'event_id' | 'owner_ids'>>;

const TasksService = {
  list: (params?: { event_id?: number; status?: TaskStatus; priority?: TaskPriority; phase?: TaskPhase }) =>
    api.get<Task[]>('/tasks', { params }).then(r => r.data),
  get: (id: number) => api.get<Task>(`/tasks/${id}`).then(r => r.data),
  create: (data: TaskCreate) => api.post<Task>('/tasks', data).then(r => r.data),
  update: (id: number, data: TaskUpdate) => api.put<Task>(`/tasks/${id}`, data).then(r => r.data),
  delete: (id: number) => api.delete(`/tasks/${id}`).then(r => r.data),
  assignVolunteer: (taskId: number, volunteerId: number) =>
    api.post<Task>(`/tasks/${taskId}/assign/${volunteerId}`).then(r => r.data),
  unassignVolunteer: (taskId: number, volunteerId: number) =>
    api.delete<Task>(`/tasks/${taskId}/assign/${volunteerId}`).then(r => r.data),
};

export default TasksService;
