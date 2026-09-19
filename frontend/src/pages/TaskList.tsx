import { useEffect, useState } from 'react';
import { CheckSquare, Plus, Search, Loader2, ChevronDown, Trash2, Check, Calendar, AlertCircle } from 'lucide-react';
import DashboardLayout from '../components/DashboardLayout';
import TasksService from '../services/tasks.service';
import type { Task, TaskCreate, TaskStatus, TaskPriority, TaskPhase } from '../services/tasks.service';
import EventsService from '../services/events.service';
import type { Event } from '../services/events.service';

const STATUS_CONFIG: Record<TaskStatus, { label: string; color: string; badge: string }> = {
  TODO: { label: 'To Do', color: 'text-slate-400', badge: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
  IN_PROGRESS: { label: 'In Progress', color: 'text-blue-400', badge: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
  DONE: { label: 'Done', color: 'text-emerald-400', badge: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
  BLOCKED: { label: 'Blocked', color: 'text-red-400', badge: 'bg-red-500/10 text-red-400 border-red-500/20' },
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
    if (!newTask.event_id) { setFormErr('Please choose an event for this task.'); return; }
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
    if (!confirm('Are you sure you want to delete this task?')) return;
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
    <DashboardLayout title="Operations Tasks">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* KPI Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Total Tasks</span>
            <p className="text-2xl font-black text-white mt-1">{tasks.length}</p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">To Do</span>
            <p className="text-2xl font-black text-slate-300 mt-1">{tasks.filter(t => t.status === 'TODO').length}</p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-400">In Progress</span>
            <p className="text-2xl font-black text-blue-400 mt-1">{tasks.filter(t => t.status === 'IN_PROGRESS').length}</p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400">Completed</span>
            <p className="text-2xl font-black text-emerald-400 mt-1">{tasks.filter(t => t.status === 'DONE').length}</p>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 col-span-2 sm:col-span-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-red-400">Blocked</span>
            <p className="text-2xl font-black text-red-400 mt-1">{tasks.filter(t => t.status === 'BLOCKED').length}</p>
          </div>
        </div>

        {/* Filters and Actions Bar */}
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              id="task-search"
              type="text"
              placeholder="Search tasks by name or description..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Event filter */}
            <div className="relative">
              <select
                id="task-event-filter"
                className="bg-slate-900 border border-slate-800 rounded-xl pl-3 pr-8 py-2.5 text-white text-xs sm:text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={eventFilter}
                onChange={e => setEventFilter(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">All Events</option>
                {events.map(ev => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            </div>

            {/* Status filter */}
            <div className="relative">
              <select
                className="bg-slate-900 border border-slate-800 rounded-xl pl-3 pr-8 py-2.5 text-white text-xs sm:text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                {Object.entries(STATUS_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            </div>

            {/* Phase filter */}
            <div className="relative">
              <select
                className="bg-slate-900 border border-slate-800 rounded-xl pl-3 pr-8 py-2.5 text-white text-xs sm:text-sm focus:outline-none focus:border-indigo-500 appearance-none"
                value={phaseFilter}
                onChange={e => setPhaseFilter(e.target.value)}
              >
                {PHASES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            </div>

            <button
              id="create-task-btn"
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl transition-all font-semibold text-xs sm:text-sm shadow-lg shadow-indigo-600/30 shrink-0"
            >
              <Plus className="w-4 h-4" /> New Task
            </button>
          </div>
        </div>

        {/* Task List Section */}
        {loading ? (
          <div className="flex justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-3xl p-12 text-center flex flex-col items-center">
            <div className="w-16 h-16 bg-slate-800/80 rounded-2xl flex items-center justify-center mb-4 text-slate-500">
              <CheckSquare className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-white mb-1">
              {search || eventFilter || statusFilter !== 'ALL' || phaseFilter !== 'ALL' ? 'No tasks match criteria' : 'No tasks created yet'}
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mb-6">
              {search ? 'Try clearing or changing your filters.' : 'Create operational tasks or launch the AI Assistant to generate a full work plan.'}
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold shadow-lg shadow-indigo-600/30"
            >
              <Plus className="w-4 h-4" /> Create First Task
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map(task => {
              const statusCfg = STATUS_CONFIG[task.status] || STATUS_CONFIG.TODO;
              const priCfg = PRIORITY_CONFIG[task.priority] || PRIORITY_CONFIG.MEDIUM;
              const isUpdating = updatingId === task.id;
              const isDeleting = deletingId === task.id;
              return (
                <div
                  key={task.id}
                  className="bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 rounded-2xl p-4 sm:p-5 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4 group shadow-sm"
                >
                  {/* Left: Status Toggle & Info */}
                  <div className="flex items-start gap-3.5 flex-1 min-w-0">
                    <button
                      onClick={() => handleStatusChange(task, task.status === 'DONE' ? 'TODO' : 'DONE')}
                      disabled={isUpdating}
                      title={task.status === 'DONE' ? 'Mark as incomplete' : 'Mark as done'}
                      className={`w-6 h-6 rounded-lg border-2 mt-0.5 flex items-center justify-center shrink-0 transition-all ${
                        task.status === 'DONE'
                          ? 'bg-emerald-500 border-emerald-500 text-white'
                          : 'border-slate-600 hover:border-emerald-500 text-transparent'
                      }`}
                    >
                      {isUpdating ? (
                        <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
                      ) : task.status === 'DONE' ? (
                        <Check className="w-4 h-4 stroke-[3]" />
                      ) : null}
                    </button>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className={`text-sm sm:text-base font-semibold ${task.status === 'DONE' ? 'line-through text-slate-500' : 'text-white'}`}>
                          {task.title}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${statusCfg.badge}`}>
                          {statusCfg.label}
                        </span>
                        {task.phase && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800/80 text-slate-400 border border-slate-700">
                            {task.phase.replace('_', ' ')}
                          </span>
                        )}
                      </div>

                      {task.description && (
                        <p className="text-xs text-slate-400 mt-1 line-clamp-1">{task.description}</p>
                      )}

                      <div className="flex items-center gap-3.5 mt-2 flex-wrap text-xs text-slate-400">
                        <span className={`flex items-center gap-1.5 font-medium ${priCfg.color}`}>
                          <span className={`w-2 h-2 rounded-full ${priCfg.dot}`} />
                          {priCfg.label} Priority
                        </span>
                        <span className="text-slate-500">·</span>
                        <span className="text-slate-400 truncate max-w-xs font-medium">
                          {getEventTitle(task.event_id)}
                        </span>
                        {task.due_date && (
                          <>
                            <span className="text-slate-500">·</span>
                            <span className="flex items-center gap-1 text-slate-400">
                              <Calendar className="w-3 h-3 text-slate-500" />
                              Due {new Date(task.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Right: Quick Status Changer & Delete Action */}
                  <div className="flex items-center gap-2 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-800/60 justify-end">
                    <div className="relative">
                      <select
                        className="bg-slate-800 hover:bg-slate-750 border border-slate-700 rounded-xl px-3 py-1.5 text-slate-200 text-xs focus:outline-none appearance-none cursor-pointer pr-7 font-medium"
                        value={task.status}
                        onChange={e => handleStatusChange(task, e.target.value as TaskStatus)}
                      >
                        {Object.entries(STATUS_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
                      </select>
                      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                    </div>

                    <button
                      onClick={() => handleDelete(task.id)}
                      disabled={isDeleting}
                      title="Delete task"
                      className="p-1.5 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-colors"
                    >
                      {isDeleting ? <Loader2 className="w-4 h-4 animate-spin text-red-400" /> : <Trash2 className="w-4 h-4" />}
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
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 w-full max-w-lg shadow-2xl space-y-5">
            <div>
              <h3 className="text-lg font-bold text-white tracking-tight">Create New Task</h3>
              <p className="text-xs text-slate-400">Add an operational task to an active event</p>
            </div>

            {formErr && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs rounded-xl px-4 py-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{formErr}</span>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Associated Event *
                </label>
                <div className="relative">
                  <select
                    id="modal-event-select"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none pr-10"
                    value={newTask.event_id || ''}
                    onChange={e => setNewTask(p => ({ ...p, event_id: Number(e.target.value) || undefined }))}
                  >
                    <option value="">-- Choose an event --</option>
                    {events.map(ev => <option key={ev.id} value={ev.id}>{ev.title}</option>)}
                  </select>
                  <ChevronDown className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Task Title *
                </label>
                <input
                  id="modal-task-title"
                  type="text"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 placeholder:text-slate-600"
                  placeholder="e.g. Set up audio mixer & wireless microphones"
                  value={newTask.title || ''}
                  onChange={e => setNewTask(p => ({ ...p, title: e.target.value }))}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Description
                </label>
                <textarea
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500 resize-none placeholder:text-slate-600"
                  placeholder="Detailed instructions or prerequisites..."
                  value={newTask.description || ''}
                  onChange={e => setNewTask(p => ({ ...p, description: e.target.value }))}
                />
              </div>

              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    Priority
                  </label>
                  <div className="relative">
                    <select
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none pr-8"
                      value={newTask.priority || 'MEDIUM'}
                      onChange={e => setNewTask(p => ({ ...p, priority: e.target.value as TaskPriority }))}
                    >
                      {Object.entries(PRIORITY_CONFIG).map(([v, c]) => <option key={v} value={v}>{c.label}</option>)}
                    </select>
                    <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                    Phase
                  </label>
                  <div className="relative">
                    <select
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-white text-sm focus:outline-none focus:border-indigo-500 appearance-none pr-8"
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
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
                  Due Date
                </label>
                <input
                  type="date"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white text-sm focus:outline-none focus:border-indigo-500"
                  value={newTask.due_date ? newTask.due_date.split('T')[0] : ''}
                  onChange={e => setNewTask(p => ({ ...p, due_date: e.target.value ? e.target.value + 'T00:00:00' : undefined }))}
                />
              </div>
            </div>

            <div className="flex items-center gap-3 pt-4 border-t border-slate-800">
              <button
                id="modal-create-task-btn"
                onClick={handleCreate}
                disabled={creating}
                className="flex-1 inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm px-4 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50"
              >
                {creating && <Loader2 className="w-4 h-4 animate-spin" />}
                {creating ? 'Creating Task...' : 'Create Task'}
              </button>
              <button
                onClick={() => { setShowModal(false); setFormErr(''); setNewTask({ status: 'TODO', priority: 'MEDIUM' }); }}
                className="text-slate-400 hover:text-white text-sm px-4 py-2.5 rounded-xl hover:bg-slate-800 transition-colors"
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
