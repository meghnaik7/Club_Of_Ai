import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import EventList from './pages/EventList';
import EventForm from './pages/EventForm';
import EventDetails from './pages/EventDetails';
import VolunteerList from './pages/VolunteerList';
import VolunteerForm from './pages/VolunteerForm';
import VolunteerProfile from './pages/VolunteerProfile';
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/events" element={<EventList />} />
            <Route path="/events/new" element={<EventForm />} />
            <Route path="/events/:id" element={<EventDetails />} />
            <Route path="/events/:id/edit" element={<EventForm />} />
            
            <Route path="/volunteers" element={<VolunteerList />} />
            <Route path="/volunteers/new" element={<VolunteerForm />} />
            <Route path="/volunteers/:id" element={<VolunteerProfile />} />
            <Route path="/volunteers/:id/edit" element={<VolunteerForm />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
