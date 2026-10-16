import React, { useState, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { useLocation } from './context/LocationContext';
import { triggerWhatsAppSos } from './utils/emergencyWhatsapp';
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
  const { latitude, longitude, locationName } = useLocation();
  const [isSosOpen, setIsSosOpen] = useState(false);

  // Immediately open WhatsApp then show the SosModal for status feedback
  const handleTriggerSos = useCallback((situationOverride) => {
    const situation = situationOverride || 'Manual SOS Trigger';
    const contacts = user?.emergency_contacts || [{ name: 'Emergency Contact', phone: '7007914594' }];
    triggerWhatsAppSos(situation, { latitude, longitude, locationName }, contacts);
    setIsSosOpen(true);
  }, [user, latitude, longitude, locationName]);

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
      <Sidebar onTriggerSos={handleTriggerSos} />

      {/* Main Content Viewport */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Header />
        
        <main style={{ flex: 1, padding: '28px', minWidth: 0 }}>
          <Routes>
            <Route path="/" element={<DashboardPage onTriggerSos={handleTriggerSos} />} />
            <Route path="/chat" element={<ChatPage onTriggerSos={handleTriggerSos} />} />
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
