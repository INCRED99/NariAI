import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useLocation } from '../context/LocationContext';
import { Sun, Moon, ShieldCheck, LogOut, Copy, Check, Navigation2 } from 'lucide-react';

const Header = ({ title = 'Dashboard' }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { latitude, longitude, locationName, isLive, copyCoordinates, copied } = useLocation();

  return (
    <header style={{
      height: '70px',
      padding: '0 28px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: 'var(--bg-card)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--border-color)',
      position: 'sticky',
      top: 0,
      zIndex: 9
    }}>
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>
          {title}
        </h2>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Exact GPS Coordinates Pill */}
        <button
          onClick={copyCoordinates}
          title="Click to copy exact GPS coordinates"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '16px',
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            fontSize: '12px',
            fontFamily: 'monospace',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <Navigation2 style={{ width: '13px', height: '13px', color: isLive ? 'var(--accent-cyan)' : 'var(--accent-amber)' }} />
          <span>{latitude.toFixed(5)}, {longitude.toFixed(5)}</span>
          {copied ? (
            <span style={{ color: 'var(--accent-green)', display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px', fontWeight: '700' }}>
              <Check style={{ width: '12px', height: '12px' }} /> Copied!
            </span>
          ) : (
            <Copy style={{ width: '12px', height: '12px', color: 'var(--text-muted)' }} />
          )}
        </button>

        {/* Safety Status Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          borderRadius: '20px',
          background: 'rgba(52, 199, 89, 0.15)',
          border: '1px solid rgba(52, 199, 89, 0.3)',
          color: 'var(--accent-green)',
          fontSize: '13px',
          fontWeight: '600'
        }}>
          <ShieldCheck style={{ width: '16px', height: '16px' }} />
          <span>Active Protection</span>
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          style={{
            background: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '10px',
            padding: '8px',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          title="Toggle Dark/Light Mode"
        >
          {theme === 'dark' ? <Sun style={{ width: '18px', height: '18px' }} /> : <Moon style={{ width: '18px', height: '18px' }} />}
        </button>

        {/* User Info Avatar & Logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingLeft: '8px', borderLeft: '1px solid var(--border-color)' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            background: 'var(--primary-gradient)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: '700',
            fontSize: '14px',
            color: '#fff'
          }}>
            {user?.name ? user.name[0].toUpperCase() : (user?.email ? user.email[0].toUpperCase() : 'U')}
          </div>
          <div style={{ maxWidth: '160px' }}>
            <p style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {user?.name || user?.email || 'User'}
            </p>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={locationName}>
              {isLive ? '📍 ' : '📍 '}{locationName}
            </p>
          </div>

          <button
            onClick={logout}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              marginLeft: '8px',
              padding: '6px'
            }}
            title="Logout"
          >
            <LogOut style={{ width: '16px', height: '16px' }} />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
