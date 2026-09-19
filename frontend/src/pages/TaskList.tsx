import { useEffect, useState } from 'react';
import { CheckSquare, Plus, Search, Loader2, ChevronDown, Trash2, Check } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import TasksService from '../services/tasks.service';
import type { Task, TaskCreate, TaskStatus, TaskPriority, TaskPhase } from '../services/tasks.service';
import EventsService from '../services/events.service';
import type { Event } from '../services/events.service';

const STATUS_CONFIG: Record<TaskStatus, { label: string; color: string }> = {
  TODO: { label: 'To Do', color: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
  IN_PROGRESS: { label: 'In Progress', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  DONE: { label: 'Done', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  BLOCKED: { label: 'Blocked', color: 'bg-red-500/10 text-red-400 border-red-500/20' },
};

const PRIORITY_CONFIG: Record<TaskPriority, { label: string; color: string; dot: string }> = {
  LOW: { label: 'Low', color: 'text-slate-400', dot: 'bg-slate-500' },
  MEDIUM: { label: 'Medium', color: 'text-yellow-400', dot: 'bg-yellow-400' },
  HIGH: { label: 'High', color: 'text-orange-400', dot: 'bg-orange-400' },
  URGENT: { label: 'Urgent', color: 'text-red-400', dot: 'bg-red-500' },
};

const PHASES: { value: string; label: string }[] = [
  { value: 'ALL', label: 'All Phases' },
  { value: 'PLANNING', label: 'Planning' },
  { value: 'EXECUTION', label: 'Execution' },
  { value: 'POST_EVENT', label: 'Post Event' },
];

export default function TaskList() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [eventFilter, setEventFilter] = useState<number | ''>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [phaseFilter, setPhaseFilter] = useState<string>('ALL');

  // New task modal state
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [formErr, setFormErr] = useState('');
  const [newTask, setNewTask] = useState<Partial<TaskCreate>>({
    status: 'TODO',
    priority: 'MEDIUM',
  });

  // Inline status change
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadTasks = () => {
    setLoading(true);
    const params: any = {};
    if (eventFilter) params.event_id = eventFilter;
    if (statusFilter !== 'ALL') params.status = statusFilter;
    if (phaseFilter !== 'ALL') params.phase = phaseFilter;
    TasksService.list(params)
      .then(setTasks)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    EventsService.list().then(setEvents).catch(() => {});
  }, []);

  useEffect(() => { loadTasks(); }, [eventFilter, statusFilter, phaseFilter]);

  const filtered = tasks.filter(t =>
    t.title.toLowerCase().includes(search.toLowerCase()) ||
    (t.description && t.description.toLowerCase().includes(search.toLowerCase()))
  );

  const handleCreate = async () => {
    if (!newTask.title?.trim()) { setFormErr('Title is required.'); return; }
    if (!newTask.event_id) { setFormErr('Select an event.'); return; }
    setCreating(true);
    setFormErr('');
    try {
      const created = await TasksService.create(newTask as TaskCreate);
      setTasks(prev => [created, ...prev]);
      setShowModal(false);
      setNewTask({ status: 'TODO', priority: 'MEDIUM' });
    } catch (e: any) {
      setFormErr(e?.response?.data?.detail || 'Failed to create task.');
    } finally {
      setCreating(false);
    }
  };

  const handleStatusChange = async (task: Task, newStatus: TaskStatus) => {
    setUpdatingId(task.id);
    try {
      const updated = await TasksService.update(task.id, { status: newStatus });
      setTasks(prev => prev.map(t => t.id === task.id ? updated : t));
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this task?')) return;
    setDeletingId(id);
    try {
      await TasksService.delete(id);
      setTasks(prev => prev.filter(t => t.id !== id));
    } finally {
      setDeletingId(null);
    }
  };

  const getEventTitle = (event_id: number) =>
    events.find(e => e.id === event_id)?.title || `Event #${event_id}`;

  return (
    <DashboardLayout title="Tasks">
      <div className="max-w-6xl mx-auto space-y-6 sm:space-y-8">
        {/* Filters bar */}
        <div className="flex flex-col lg:flex-row items-stretch gap-3 sm:gap-3.5">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              id="task-search"
              type="text"
              placeholder="Search tasks..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors placeholder-slate-500"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap sm:flex-nowrap items-center gap-2.5">
            {/* Event filter */}
            <div className="relative flex-1 sm:flex-initial">
              <select
                id="task-event-filter"
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-3.5 pr-8 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={eventFilter}
                onChange={e => setEventFilter(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">All Events</option>
                {events.map(ev => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            </div>
            {/* Status filter */}
            <div className="relative flex-1 sm:flex-initial">
              <select
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-3.5 pr-8 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                {Object.entries(STATUS_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            </div>
            {/* Phase filter */}
            <div className="relative flex-1 sm:flex-initial">
              <select
                className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-3.5 pr-8 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={phaseFilter}
                onChange={e => setPhaseFilter(e.target.value)}
              >
                {PHASES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
            </div>
            <button
              id="create-task-btn"
              onClick={() => setShowModal(true)}
              className="w-full sm:w-auto flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl transition-colors font-semibold text-sm shrink-0 shadow-md shadow-indigo-600/20"
            >
              <Plus className="w-4 h-4" /> New Task
            </button>
          </div>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
          {Object.entries(STATUS_CONFIG).map(([status, cfg]) => {
            const count = tasks.filter(t => t.status === status).length;
            return (
              <div key={status} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-sm">
                <p className="text-xs text-slate-400 font-medium mb-1">{cfg.label}</p>
                <p className="text-2xl font-bold text-white tracking-tight">{count}</p>
              </div>
            );
          })}
        </div>

        {/* Task List */}
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center">
            <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
              <CheckSquare className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">
              {search ? 'No matching tasks found' : 'No tasks yet'}
            </h3>
            <p className="text-slate-400 text-sm max-w-sm">
              {search ? 'Try different keywords or reset filters.' : 'Create a task or use the AI assistant to generate a task plan.'}
            </p>
          </div>
        ) : (
          <div className="space-y-2.5 sm:space-y-3">
            {filtered.map(task => {
              const statusCfg = STATUS_CONFIG[task.status];
              const priCfg = PRIORITY_CONFIG[task.priority];
              const isUpdating = updatingId === task.id;
              const isDeleting = deletingId === task.id;
              return (
                <div
                  key={task.id}
                  className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-4 sm:px-5 sm:py-4 transition-all group flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 shadow-sm"
                >
                  <div className="flex items-start sm:items-center gap-3.5 flex-1 min-w-0">
                    {/* Status toggle (click to mark done) */}
                    <button
                      onClick={() => handleStatusChange(task, task.status === 'DONE' ? 'TODO' : 'DONE')}
                      disabled={isUpdating}
                      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all mt-0.5 sm:mt-0 ${
                        task.status === 'DONE'
                          ? 'bg-emerald-500 border-emerald-500 shadow-sm'
                          : 'border-slate-600 hover:border-emerald-500'
                      }`}
                      aria-label="Toggle task completion status"
                    >
                      {isUpdating ? (
                        <Loader2 className="w-3 h-3 text-white animate-spin" />
                      ) : task.status === 'DONE' ? (
                        <Check className="w-3 h-3 text-white" />
                      ) : null}
                    </button>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-sm font-semibold text-white ${task.status === 'DONE' ? 'line-through text-slate-500' : ''}`}>
                          {task.title}
                        </span>
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider ${statusCfg.color}`}>
                          {statusCfg.label}
                        </span>
                        {task.phase && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                            {task.phase.replace('_', ' ')}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                        <span className={`text-xs flex items-center gap-1.5 font-medium ${priCfg.color}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${priCfg.dot}`} />
                          {priCfg.label}
                        </span>
                        <span className="text-xs text-slate-500">
                          {getEventTitle(task.event_id)}
                        </span>
                        {task.due_date && (
                          <span className="text-xs text-slate-500">
                            Due {new Date(task.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                        )}
                        {task.assignments.length > 0 && (
                          <span className="text-xs text-slate-500">
                            {task.assignments.length} assignee{task.assignments.length > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions (visible on mobile, hover on desktop) */}
                  <div className="flex items-center justify-end gap-2 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-800/60 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                    {/* Inline status quick-change */}
                    <div className="relative">
                      <select
                        className="bg-slate-800 border border-slate-700 rounded-lg pl-2.5 pr-6 py-1.5 text-slate-300 text-xs focus:outline-none appearance-none cursor-pointer"
                        value={task.status}
                        onChange={e => handleStatusChange(task, e.target.value as TaskStatus)}
                        onClick={e => e.stopPropagation()}
                      >
                        {Object.entries(STATUS_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
                      </select>
                      <ChevronDown className="absolute right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-400 pointer-events-none" />
                    </div>
                    <button
                      onClick={() => handleDelete(task.id)}
                      disabled={isDeleting}
                      className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                      title="Delete task"
                    >
                      {isDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Task Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-7 w-full max-w-lg shadow-2xl space-y-4">
            <h3 className="text-white font-semibold text-lg">Create New Task</h3>
            {formErr && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm rounded-xl px-3.5 py-2.5">{formErr}</div>
            )}
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Event *</label>
                <div className="relative">
                  <select
                    id="modal-event-select"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                    value={newTask.event_id || ''}
                    onChange={e => setNewTask(p => ({ ...p, event_id: Number(e.target.value) || undefined }))}
                  >
                    <option value="">Select event…</option>
                    {events.map(ev => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Title *</label>
                <input
                  id="modal-task-title"
                  type="text"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder-slate-500"
                  placeholder="Task title"
                  value={newTask.title || ''}
                  onChange={e => setNewTask(p => ({ ...p, title: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Description</label>
                <textarea
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none placeholder-slate-500"
                  placeholder="Optional description"
                  value={newTask.description || ''}
                  onChange={e => setNewTask(p => ({ ...p, description: e.target.value }))}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Priority</label>
                  <div className="relative">
                    <select
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                      value={newTask.priority || 'MEDIUM'}
                      onChange={e => setNewTask(p => ({ ...p, priority: e.target.value as TaskPriority }))}
                    >
                      {Object.entries(PRIORITY_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">Phase</label>
                  <div className="relative">
                    <select
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                      value={newTask.phase || ''}
                      onChange={e => setNewTask(p => ({ ...p, phase: (e.target.value as TaskPhase) || undefined }))}
                    >
                      <option value="">No phase</option>
                      {PHASES.slice(1).map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Due Date</label>
                <input
                  type="date"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={newTask.due_date ? newTask.due_date.split('T')[0] : ''}
                  onChange={e => setNewTask(p => ({ ...p, due_date: e.target.value ? e.target.value + 'T00:00:00' : undefined }))}
                />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                id="modal-create-task-btn"
                onClick={handleCreate}
                disabled={creating}
                className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors shadow-md shadow-indigo-600/20"
              >
                {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                Create Task
              </button>
              <button
                onClick={() => { setShowModal(false); setFormErr(''); setNewTask({ status: 'TODO', priority: 'MEDIUM' }); }}
                className="text-slate-400 hover:text-white text-sm px-4 py-2.5 rounded-xl hover:bg-slate-800 transition-colors font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
