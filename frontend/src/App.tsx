import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import EventList from './pages/EventList';
import EventForm from './pages/EventForm';
import EventDetails from './pages/EventDetails';
import VolunteerList from './pages/VolunteerList';
import VolunteerForm from './pages/VolunteerForm';
import VolunteerProfile from './pages/VolunteerProfile';
import AnnouncementList from './pages/AnnouncementList';
import AnnouncementForm from './pages/AnnouncementForm';
import TaskList from './pages/TaskList';
import TeamManagement from './pages/TeamManagement';
import PermissionManagement from './pages/PermissionManagement';
import AdminOrganization from './pages/AdminOrganization';
import DocumentList from './pages/DocumentList';
import Profile from './pages/Profile';
import AgenticAI from './pages/AgenticAI';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/profile" element={<Profile />} />

            {/* Admin Organization & Hierarchy */}
            <Route path="/admin/organization" element={<AdminOrganization />} />

            {/* Teams */}
            <Route path="/teams" element={<TeamManagement />} />

            {/* Permissions & Overrides */}
            <Route path="/permissions" element={<PermissionManagement />} />

            {/* Events */}
            <Route path="/events" element={<EventList />} />
            <Route path="/events/new" element={<EventForm />} />
            <Route path="/events/:id" element={<EventDetails />} />
            <Route path="/events/:id/edit" element={<EventForm />} />

            {/* Volunteers */}
            <Route path="/volunteers" element={<VolunteerList />} />
            <Route path="/volunteers/new" element={<VolunteerForm />} />
            <Route path="/volunteers/:id" element={<VolunteerProfile />} />
            <Route path="/volunteers/:id/edit" element={<VolunteerForm />} />

            {/* Announcements */}
            <Route path="/announcements" element={<AnnouncementList />} />
            <Route path="/announcements/new" element={<AnnouncementForm />} />
            <Route path="/announcements/:id/edit" element={<AnnouncementForm />} />

            {/* Tasks */}
            <Route path="/tasks" element={<TaskList />} />

            {/* Agentic AI Operations */}
            <Route path="/agentic-ai" element={<AgenticAI />} />

            {/* Documents & RAG Knowledge Brain */}
            <Route path="/documents" element={<DocumentList />} />
          </Route>

        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
