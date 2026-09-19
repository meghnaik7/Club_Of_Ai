import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
