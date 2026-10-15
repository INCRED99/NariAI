import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import SosModal from './components/SosModal';

import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import RouteSafetyPage from './pages/RouteSafetyPage';
import NearbyPage from './pages/NearbyPage';
import EmergencyPage from './pages/EmergencyPage';
import ProfilePage from './pages/ProfilePage';
import SettingsPage from './pages/SettingsPage';

const AppLayout = () => {
  const { user, token, loading } = useAuth();
  const [isSosOpen, setIsSosOpen] = useState(false);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)', color: '#fff' }}>
        <p style={{ fontSize: '18px', fontWeight: '600' }}>Initializing Nari Safety Sentinel...</p>
      </div>
    );
  }

  // Require user authentication: first login must take place (no fallback user)
  if (!token || !user) {
    return <AuthPage />;
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Navigation Sidebar */}
      <Sidebar onTriggerSos={() => setIsSosOpen(true)} />

      {/* Main Content Viewport */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Header />
        
        <main style={{ flex: 1, padding: '28px', minWidth: 0 }}>
          <Routes>
            <Route path="/" element={<DashboardPage onTriggerSos={() => setIsSosOpen(true)} />} />
            <Route path="/chat" element={<ChatPage onTriggerSos={() => setIsSosOpen(true)} />} />
            <Route path="/routes" element={<RouteSafetyPage />} />
            <Route path="/nearby" element={<NearbyPage />} />
            <Route path="/emergency" element={<EmergencyPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>

      {/* Global Emergency Modal */}
      <SosModal isOpen={isSosOpen} onClose={() => setIsSosOpen(false)} />
    </div>
  );
};

import { LocationProvider } from './context/LocationContext';

function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <LocationProvider>
          <Router>
            <AppLayout />
          </Router>
        </LocationProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}

export default App;
