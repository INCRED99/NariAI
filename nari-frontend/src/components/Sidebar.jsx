import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Shield, 
  LayoutDashboard, 
  Bot, 
  MapPin, 
  Navigation, 
  AlertTriangle, 
  User, 
  Settings, 
  Radio
} from 'lucide-react';

const Sidebar = ({ onTriggerSos }) => {
  const navItems = [
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/chat', label: 'AI Assistant', icon: Bot },
    { path: '/routes', label: 'Route Safety', icon: Navigation },
    { path: '/nearby', label: 'Nearby Havens', icon: MapPin },
    { path: '/emergency', label: 'Emergency Hub', icon: Radio },
    { path: '/profile', label: 'My Profile', icon: User },
    { path: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside style={{
      width: '260px',
      height: '100vh',
      position: 'sticky',
      top: 0,
      display: 'flex',
      flexDirection: 'column',
      padding: '24px 16px',
      background: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-color)',
      zIndex: 10
    }}>
      {/* Brand Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '0 12px 28px 12px' }}>
        <div style={{
          width: '42px',
          height: '42px',
          borderRadius: '12px',
          background: 'var(--primary-gradient)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: 'var(--shadow-glow)'
        }}>
          <Shield style={{ color: '#fff', width: '24px', height: '24px' }} />
        </div>
        <div>
          <h1 style={{ fontSize: '22px', fontWeight: '800', letterSpacing: '0.5px', background: 'var(--primary-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            NARI
          </h1>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '500' }}>Women Safety Network</p>
        </div>
      </div>

      {/* Quick SOS Trigger Button in Sidebar */}
      <button 
        onClick={onTriggerSos}
        className="emergency-btn pulse-emergency"
        style={{
          width: '100%',
          padding: '14px',
          fontSize: '15px',
          marginBottom: '24px',
          borderRadius: '14px'
        }}
      >
        <AlertTriangle style={{ width: '20px', height: '20px' }} />
        TRIGGER SOS
      </button>

      {/* Navigation Links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: 1 }}>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '14px',
                padding: '12px 16px',
                borderRadius: '12px',
                color: isActive ? '#ffffff' : 'var(--text-secondary)',
                background: isActive ? 'var(--primary-gradient)' : 'transparent',
                fontWeight: isActive ? '600' : '400',
                textDecoration: 'none',
                transition: 'all 0.2s ease',
                boxShadow: isActive ? 'var(--shadow-glow)' : 'none'
              })}
            >
              <Icon style={{ width: '20px', height: '20px' }} />
              <span style={{ fontSize: '14px' }}>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Live Protection Status */}
      <div className="glass-panel" style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--accent-green)', boxShadow: '0 0 10px var(--accent-green)' }} />
        <div>
          <p style={{ fontSize: '12px', fontWeight: '600', margin: 0, color: 'var(--text-primary)' }}>Active Protection</p>
          <p style={{ fontSize: '10px', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>Safety Shield Online</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
