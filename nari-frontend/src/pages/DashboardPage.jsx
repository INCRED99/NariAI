import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useLocation } from '../context/LocationContext';
import ThreatGauge from '../components/ThreatGauge';
import {
  ShieldCheck,
  PhoneCall,
  Key,
  Cpu,
  Navigation,
  Bot,
  AlertTriangle,
  ArrowUpRight,
  Activity,
  MapPin,
  Copy,
  Check,
  RotateCw,
  ExternalLink,
  Crosshair,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { createUserLocationIcon } from '../utils/leafletIcons';

const DashboardPage = ({ onTriggerSos }) => {
  const { user } = useAuth();
  const {
    latitude,
    longitude,
    accuracy,
    locationName,
    formattedCoords,
    isLive,
    loading,
    refreshLocation,
    copyCoordinates,
    copied,
  } = useLocation();

  const userIcon = createUserLocationIcon();

  const recentIncidents = [
    { id: 1, title: 'Unlit street reported near Central Park', time: '10 mins ago', category: 'Lighting', level: 'Low' },
    { id: 2, title: 'Suspicious gathering near Metro Gate 3', time: '25 mins ago', category: 'Crowd Risk', level: 'Medium' },
    { id: 3, title: 'Women Police Patrol active on Expressway', time: '1 hour ago', category: 'Patrol', level: 'Safe' },
  ];

  const osmUrl = `https://www.openstreetmap.org/?mlat=${latitude.toFixed(6)}&mlon=${longitude.toFixed(6)}#map=17/${latitude.toFixed(6)}/${longitude.toFixed(6)}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', paddingBottom: '40px' }}>
      {/* Top Banner */}
      <div className="glass-panel" style={{
        padding: '24px 32px',
        background: 'linear-gradient(135deg, rgba(122, 92, 255, 0.15) 0%, rgba(0, 198, 255, 0.15) 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        <div>
          <h2 style={{ fontSize: '24px', fontWeight: '800', marginBottom: '6px' }}>
            Welcome back, {user?.name ? user.name.split(' ')[0] : (user?.email ? user.email.split('@')[0] : 'there')} 👋
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Nari AI Sentinel is actively monitoring your location & surrounding safety signals.
          </p>
        </div>

        <button
          onClick={onTriggerSos}
          className="emergency-btn pulse-emergency"
          style={{ padding: '14px 28px', fontSize: '16px' }}
        >
          <AlertTriangle style={{ width: '22px', height: '22px' }} />
          INSTANT SOS EMERGENCY
        </button>
      </div>

      {/* Main Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
        
        {/* Threat Assessment Gauge Card */}
        <div className="glass-panel" style={{ padding: '28px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
          <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>Real-Time Threat Gauge</span>
            <span
              onClick={refreshLocation}
              style={{
                fontSize: '11px',
                color: isLive ? 'var(--accent-green)' : 'var(--accent-amber)',
                background: isLive ? 'rgba(52, 199, 89, 0.15)' : 'rgba(255, 149, 0, 0.15)',
                padding: '4px 10px',
                borderRadius: '12px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
              title="Click to refresh GPS location"
            >
              {isLive ? '● GPS Live' : '● Demo Location'}
            </span>
          </div>

          <ThreatGauge score={15} state="Normal" />

          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '16px' }}>
            Area: <strong style={{ color: 'var(--text-primary)' }}>{locationName}</strong> — Surroundings verified safe.
          </p>
        </div>

        {/* Quick Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(52, 199, 89, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-green)', marginBottom: '12px' }}>
              <ShieldCheck style={{ width: '20px', height: '20px' }} />
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Status</p>
            <p style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>Active Shield</p>
          </div>

          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(122, 92, 255, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-purple)', marginBottom: '12px' }}>
              <Key style={{ width: '20px', height: '20px' }} />
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Safe Word</p>
            <p style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>"{user?.safe_word || 'Blue Moon'}"</p>
          </div>

          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(0, 198, 255, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-cyan)', marginBottom: '12px' }}>
              <PhoneCall style={{ width: '20px', height: '20px' }} />
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Contacts</p>
            <p style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '2px' }}>2 Trusted</p>
          </div>

          <div className="glass-panel" style={{ padding: '20px' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(52, 199, 89, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-green)', marginBottom: '12px' }}>
              <ShieldCheck style={{ width: '20px', height: '20px' }} />
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Protection</p>
            <p style={{ fontSize: '16px', fontWeight: '700', color: 'var(--accent-green)', marginTop: '2px' }}>Active</p>
          </div>
        </div>

      </div>

      {/* Exact Live GPS Coordinates & OpenStreetMap Card */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'rgba(0, 198, 255, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--accent-cyan)' }}>
              <Crosshair style={{ width: '20px', height: '20px' }} />
            </div>
            <div>
              <h3 style={{ fontSize: '17px', fontWeight: '700', color: 'var(--text-primary)' }}>
                Exact Device GPS & OpenStreetMap
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                High-precision coordinates resolved via OpenStreetMap Nominatim
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={refreshLocation}
              disabled={loading}
              className="glass-btn"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '10px',
                fontSize: '12px',
                fontWeight: '600',
                cursor: 'pointer',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
              }}
              title="Refresh GPS Coordinates"
            >
              <RotateCw style={{ width: '14px', height: '14px', animation: loading ? 'spin 1s infinite linear' : 'none' }} />
              {loading ? 'Locating...' : 'Refresh GPS'}
            </button>

            <button
              onClick={copyCoordinates}
              className="gradient-btn"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                fontSize: '12px',
                borderRadius: '10px',
              }}
            >
              {copied ? <Check style={{ width: '14px', height: '14px' }} /> : <Copy style={{ width: '14px', height: '14px' }} />}
              {copied ? 'Copied Coordinates!' : 'Copy Exact Coords'}
            </button>

            <a
              href={osmUrl}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '10px',
                fontSize: '12px',
                fontWeight: '600',
                textDecoration: 'none',
                background: 'rgba(52, 199, 89, 0.15)',
                border: '1px solid rgba(52, 199, 89, 0.3)',
                color: 'var(--accent-green)',
              }}
              title="Open full view on OpenStreetMap"
            >
              <ExternalLink style={{ width: '14px', height: '14px' }} />
              OpenStreetMap
            </a>
          </div>
        </div>

        {/* Coordinates Display Bars */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '14px',
          marginBottom: '18px'
        }}>
          <div style={{ background: 'var(--bg-input)', padding: '14px 18px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: '700' }}>
              Latitude (Exact)
            </p>
            <p style={{ fontSize: '18px', fontWeight: '800', fontFamily: 'monospace', color: 'var(--accent-cyan)', marginTop: '4px' }}>
              {latitude.toFixed(6)}°
            </p>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '14px 18px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: '700' }}>
              Longitude (Exact)
            </p>
            <p style={{ fontSize: '18px', fontWeight: '800', fontFamily: 'monospace', color: 'var(--accent-cyan)', marginTop: '4px' }}>
              {longitude.toFixed(6)}°
            </p>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '14px 18px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: '700' }}>
              GPS Precision / Accuracy
            </p>
            <p style={{ fontSize: '15px', fontWeight: '700', color: 'var(--accent-green)', marginTop: '6px' }}>
              ± {accuracy} meters ({isLive ? 'Live Sensor' : 'Reference Point'})
            </p>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '14px 18px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: '700' }}>
              Resolved Address (OSM)
            </p>
            <p style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)', marginTop: '6px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={locationName}>
              📍 {locationName}
            </p>
          </div>
        </div>

        {/* Embedded Leaflet OpenStreetMap */}
        <div style={{ height: '240px', width: '100%', borderRadius: '14px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
          <MapContainer
            key={`${latitude}-${longitude}`}
            center={[latitude, longitude]}
            zoom={15}
            scrollWheelZoom={false}
            style={{ width: '100%', height: '100%' }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            <Marker position={[latitude, longitude]} icon={userIcon}>
              <Popup>
                <div style={{ padding: '4px' }}>
                  <strong style={{ fontSize: '13px' }}>📍 Your Exact Position</strong><br />
                  <span style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontFamily: 'monospace' }}>
                    {latitude.toFixed(6)}, {longitude.toFixed(6)}
                  </span><br />
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{locationName}</span>
                </div>
              </Popup>
            </Marker>
          </MapContainer>
        </div>
      </div>

      {/* Quick Launch Cards */}
      <h3 style={{ fontSize: '18px', fontWeight: '700', marginTop: '8px' }}>Safety Hub Quick Actions</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px' }}>
        
        <Link to="/chat" style={{ textDecoration: 'none' }}>
          <div className="glass-panel" style={{ padding: '24px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                <Bot style={{ width: '24px', height: '24px' }} />
              </div>
              <ArrowUpRight style={{ color: 'var(--text-muted)', width: '20px', height: '20px' }} />
            </div>
            <h4 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '16px' }}>AI Companion</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Real-time voice & text safety companion</p>
          </div>
        </Link>

        <Link to="/nearby" style={{ textDecoration: 'none' }}>
          <div className="glass-panel" style={{ padding: '24px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'linear-gradient(135deg, #34C759 0%, #00C6FF 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                <MapPin style={{ width: '24px', height: '24px' }} />
              </div>
              <ArrowUpRight style={{ color: 'var(--text-muted)', width: '20px', height: '20px' }} />
            </div>
            <h4 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '16px' }}>Safety Havens</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Locate police booths, hospitals & safe spots around you</p>
          </div>
        </Link>

        <Link to="/routes" style={{ textDecoration: 'none' }}>
          <div className="glass-panel" style={{ padding: '24px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'linear-gradient(135deg, #00C6FF 0%, #0072FF 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                <Navigation style={{ width: '24px', height: '24px' }} />
              </div>
              <ArrowUpRight style={{ color: 'var(--text-muted)', width: '20px', height: '20px' }} />
            </div>
            <h4 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '16px' }}>Safe Route Planner</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Analyze lighting, crowds & safety before walking</p>
          </div>
        </Link>

        <Link to="/emergency" style={{ textDecoration: 'none' }}>
          <div className="glass-panel" style={{ padding: '24px', cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ width: '44px', height: '44px', borderRadius: '12px', background: 'var(--emergency-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                <Activity style={{ width: '24px', height: '24px' }} />
              </div>
              <ArrowUpRight style={{ color: 'var(--text-muted)', width: '20px', height: '20px' }} />
            </div>
            <h4 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)', marginTop: '16px' }}>Emergency Hub</h4>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>Instant WhatsApp distress dispatch with live GPS location</p>
          </div>
        </Link>

      </div>

      {/* Incident Stream */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '16px' }}>Live Community Safety Alerts</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {recentIncidents.map((inc) => (
            <div key={inc.id} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 18px',
              borderRadius: '12px',
              background: 'var(--bg-input)'
            }}>
              <div>
                <p style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>{inc.title}</p>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>Category: {inc.category} • {inc.time}</p>
              </div>
              <span style={{
                fontSize: '11px',
                fontWeight: '700',
                padding: '4px 10px',
                borderRadius: '8px',
                background: inc.level === 'Low' ? 'rgba(255, 149, 0, 0.15)' : inc.level === 'Medium' ? 'rgba(255, 59, 48, 0.15)' : 'rgba(52, 199, 89, 0.15)',
                color: inc.level === 'Low' ? 'var(--accent-amber)' : inc.level === 'Medium' ? 'var(--accent-red)' : 'var(--accent-green)'
              }}>
                {inc.level} Risk
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
