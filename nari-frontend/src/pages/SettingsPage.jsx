import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Settings, Moon, Sun, Save, Check, Bell, Shield, Volume2, Phone, ChevronRight, User } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';

const SettingsPage = () => {
  const { theme, toggleTheme } = useTheme();
  const { user } = useAuth();
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [autoOpenWa, setAutoOpenWa] = useState(true);
  const [saved, setSaved] = useState(false);

  const contacts = user?.emergency_contacts || [];

  const handleSaveSettings = (e) => {
    e.preventDefault();
    localStorage.setItem('nari_sound_alerts', soundEnabled ? 'true' : 'false');
    localStorage.setItem('nari_auto_open_wa', autoOpenWa ? 'true' : 'false');
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div style={{ maxWidth: '720px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px', paddingBottom: '40px' }}>
      
      <div className="glass-panel" style={{ padding: '28px' }}>
        <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Settings style={{ color: 'var(--accent-purple)', width: '22px', height: '22px' }} />
          App Preferences
        </h3>

        {saved && (
          <div style={{ padding: '10px 14px', borderRadius: '10px', background: 'rgba(52, 199, 89, 0.15)', color: 'var(--accent-green)', fontSize: '13px', fontWeight: '600', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Check style={{ width: '16px', height: '16px' }} />
            Preferences saved successfully!
          </div>
        )}

        <form onSubmit={handleSaveSettings} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Theme Selector */}
          <div style={{ padding: '18px 20px', borderRadius: '12px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>Interface Theme</p>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Current: {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</p>
            </div>
            <button
              type="button"
              onClick={toggleTheme}
              className="gradient-btn"
              style={{ padding: '10px 18px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              {theme === 'dark' ? <Sun style={{ width: '16px', height: '16px' }} /> : <Moon style={{ width: '16px', height: '16px' }} />}
              Switch to {theme === 'dark' ? 'Light' : 'Dark'}
            </button>
          </div>

          {/* Instant WhatsApp Dispatch */}
          <div style={{ padding: '18px 20px', borderRadius: '12px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
              <Shield style={{ width: '20px', height: '20px', color: 'var(--accent-green)', marginTop: '2px', flexShrink: 0 }} />
              <div>
                <p style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>Instant WhatsApp SOS</p>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Automatically open WhatsApp to your primary emergency contact when SOS triggers</p>
              </div>
            </div>
            <label style={{ position: 'relative', display: 'inline-block', width: '44px', height: '24px', cursor: 'pointer', flexShrink: 0 }}>
              <input
                type="checkbox"
                checked={autoOpenWa}
                onChange={(e) => setAutoOpenWa(e.target.checked)}
                style={{ opacity: 0, width: 0, height: 0 }}
              />
              <span style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                borderRadius: '24px',
                background: autoOpenWa ? 'var(--accent-green)' : 'rgba(255, 255, 255, 0.2)',
                transition: '0.2s',
              }}>
                <span style={{
                  position: 'absolute', content: '""', height: '18px', width: '18px', left: autoOpenWa ? '22px' : '3px', bottom: '3px',
                  background: 'white', borderRadius: '50%', transition: '0.2s',
                }} />
              </span>
            </label>
          </div>

          {/* Sound Alerts */}
          <div style={{ padding: '18px 20px', borderRadius: '12px', background: 'var(--bg-input)', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
              <Volume2 style={{ width: '20px', height: '20px', color: 'var(--accent-cyan)', marginTop: '2px', flexShrink: 0 }} />
              <div>
                <p style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>Audible Alerts & Feedback</p>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Play alert chimes upon emergency dispatch confirmation</p>
              </div>
            </div>
            <label style={{ position: 'relative', display: 'inline-block', width: '44px', height: '24px', cursor: 'pointer', flexShrink: 0 }}>
              <input
                type="checkbox"
                checked={soundEnabled}
                onChange={(e) => setSoundEnabled(e.target.checked)}
                style={{ opacity: 0, width: 0, height: 0 }}
              />
              <span style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                borderRadius: '24px',
                background: soundEnabled ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.2)',
                transition: '0.2s',
              }}>
                <span style={{
                  position: 'absolute', content: '""', height: '18px', width: '18px', left: soundEnabled ? '22px' : '3px', bottom: '3px',
                  background: 'white', borderRadius: '50%', transition: '0.2s',
                }} />
              </span>
            </label>
          </div>

          <button type="submit" className="gradient-btn" style={{ width: '100%', padding: '14px', marginTop: '10px' }}>
            <Save style={{ width: '18px', height: '18px' }} />
            Save Preferences
          </button>

        </form>
      </div>

      {/* Emergency Contacts Overview in Settings */}
      <div className="glass-panel" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
            <Phone style={{ color: 'var(--accent-cyan)', width: '20px', height: '20px' }} />
            Emergency Contacts
          </h3>
          <Link
            to="/profile"
            className="gradient-btn"
            style={{ padding: '8px 16px', fontSize: '12px', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            Manage Contacts <ChevronRight style={{ width: '14px', height: '14px' }} />
          </Link>
        </div>

        <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
          SOS alerts and live location updates are sent to these contacts. Manage or add new contacts in your Profile.
        </p>

        {contacts.length === 0 ? (
          <div style={{ padding: '18px', borderRadius: '12px', background: 'rgba(255, 149, 0, 0.08)', border: '1px solid rgba(255, 149, 0, 0.35)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ fontSize: '14px', fontWeight: '700', color: '#FF9500', margin: 0 }}>No emergency contacts saved</p>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>Add at least one contact so Nari AI can trigger instant WhatsApp dispatch.</p>
            </div>
            <Link
              to="/profile"
              className="gradient-btn"
              style={{ padding: '8px 14px', fontSize: '12px', textDecoration: 'none' }}
            >
              Add Now
            </Link>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {contacts.map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderRadius: '12px', background: 'var(--bg-input)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <User style={{ width: '18px', height: '18px', color: i === 0 ? 'var(--accent-green)' : 'var(--text-muted)' }} />
                  <div>
                    <span style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>{c.name}</span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>({c.relation}) • {c.phone}</span>
                  </div>
                </div>
                {i === 0 && (
                  <span style={{ fontSize: '10px', padding: '2px 8px', borderRadius: '10px', background: 'rgba(37, 211, 102, 0.2)', color: '#25D366', fontWeight: '700' }}>
                    Primary SOS Dispatch
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  );
};

export default SettingsPage;
