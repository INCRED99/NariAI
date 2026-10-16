import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, PhoneCall, MapPin, X, CheckCircle, RefreshCw, AlertCircle, MessageCircle } from 'lucide-react';
import client from '../api/client';
import { useLocation } from '../context/LocationContext';
import { useAuth } from '../context/AuthContext';

import { triggerWhatsAppSos, cleanPhone } from '../utils/emergencyWhatsapp';

const SosModal = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sosResponse, setSosResponse] = useState(null);
  const [waOpened, setWaOpened] = useState(false);

  const { latitude, longitude, locationName } = useLocation();
  const { user } = useAuth();

  // Helper to generate a local WhatsApp link (fallback when backend is offline)
  const generateLocalWaLink = useCallback((phone, message) => {
    let clean = phone.replace(/[\s\-\(\)]/g, '');
    if (clean.startsWith('+')) clean = clean.substring(1);
    if (clean.length === 10 && '6789'.includes(clean[0])) clean = '91' + clean;
    return `https://wa.me/${clean}?text=${encodeURIComponent(message)}`;
  }, []);

  // Build the emergency message text
  const buildEmergencyMessage = useCallback(() => {
    return (
      `🚨 NARI SOS ALERT!\n` +
      `I need URGENT help!\n\n` +
      `📍 Location: ${locationName}\n` +
      `🗺️ GPS: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}\n` +
      `⏰ Time: ${new Date().toLocaleTimeString()}\n\n` +
      `Live Map: https://www.openstreetmap.org/?mlat=${latitude.toFixed(6)}&mlon=${longitude.toFixed(6)}#map=18/${latitude.toFixed(6)}/${longitude.toFixed(6)}\n\n` +
      `Please send help immediately! Call me or come to my location!`
    );
  }, [latitude, longitude, locationName]);

  // Auto-open WhatsApp for all contacts
  const openWhatsAppForContacts = useCallback((whatsappLinks) => {
    if (waOpened || !whatsappLinks || whatsappLinks.length === 0) return;

    // Open the first contact's WhatsApp immediately
    if (whatsappLinks[0]?.wa_link) {
      window.open(whatsappLinks[0].wa_link, '_blank');
    }

    // Open additional contacts with a slight delay so browser doesn't block popups
    whatsappLinks.slice(1).forEach((link, idx) => {
      if (link?.wa_link) {
        setTimeout(() => {
          window.open(link.wa_link, '_blank');
        }, (idx + 1) * 800);
      }
    });

    setWaOpened(true);
  }, [waOpened]);

  // Fallback / instant WhatsApp opener
  const openWhatsAppFallback = useCallback(() => {
    const contacts = user?.emergency_contacts?.length > 0 ? user.emergency_contacts : [];
    if (contacts.length === 0) {
      setWaOpened(true);
      return; // No contacts set — skip dispatch
    }
    triggerWhatsAppSos('Emergency SOS Triggered', { latitude, longitude, locationName }, contacts);
    setWaOpened(true);
  }, [user, latitude, longitude, locationName]);

  const triggerSos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await client.post('/sos', {
        situation: 'Manual UI Emergency Trigger',
        latitude: latitude,
        longitude: longitude,
        location_name: locationName,
        trigger_type: 'Manual UI Trigger',
        user_id: user?.uid || user?.email || 'user'
      });

      if (res.data && res.data.success) {
        setSosResponse(res.data);
      } else {
        setError('Server returned unsuccessful response.');
      }
    } catch (err) {
      console.error('SOS dispatch error:', err);
      const errMsg = err.response?.data?.detail || err.message || 'Unknown error';
      setError(`SOS backend issue: ${errMsg}`);
    } finally {
      setLoading(false);
    }
  }, [latitude, longitude, locationName, user]);

  // ── IMMEDIATE WhatsApp & backend dispatch on modal open (no countdown, no delay) ──
  useEffect(() => {
    if (isOpen) {
      if (!waOpened) {
        openWhatsAppFallback();
      }
      triggerSos();
    } else {
      setWaOpened(false);
      setError(null);
      setSosResponse(null);
    }
  }, [isOpen, waOpened, openWhatsAppFallback, triggerSos]);
  // ─────────────────────────────────────────────────────────────────────────────

  const handleRetry = () => {
    setError(null);
    setSosResponse(null);
    setWaOpened(false);
    triggerSos();
    openWhatsAppFallback();
  };

  const handleCancel = () => {
    setError(null);
    setSosResponse(null);
    setWaOpened(false);
    onClose();
  };

  if (!isOpen) return null;

  // Derive contact names from response or user profile (no fallback)
  const contactNames = sosResponse?.contacts?.map(c => c.name).join(' & ')
    || user?.emergency_contacts?.map(c => c.name).join(' & ')
    || null;

  // Build WhatsApp links for display (from backend response or user contacts only)
  const displayWaLinks = sosResponse?.whatsapp_links?.length > 0
    ? sosResponse.whatsapp_links
    : (user?.emergency_contacts?.length > 0 ? user.emergency_contacts : []).map(c => ({
        name: c.name,
        phone: c.phone,
        wa_link: generateLocalWaLink(c.phone, `🚨 SOS for ${c.name}!\n\n${buildEmergencyMessage()}`)
      }));



  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.85)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div className="glass-panel" style={{
        maxWidth: '480px',
        width: '100%',
        padding: '32px',
        textAlign: 'center',
        border: `2px solid ${error ? 'var(--accent-amber)' : 'var(--accent-red)'}`,
        boxShadow: 'var(--shadow-emergency)',
        maxHeight: '90vh',
        overflowY: 'auto'
      }}>
        <>
            <div style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              background: error ? 'var(--warning-gradient)' : 'var(--success-gradient)',
              margin: '0 auto 20px auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              {error ? (
                <AlertCircle style={{ width: '40px', height: '40px', color: '#fff' }} />
              ) : (
                <CheckCircle style={{ width: '40px', height: '40px', color: '#fff' }} />
              )}
            </div>

            <h3 style={{ fontSize: '22px', fontWeight: '800', color: error ? 'var(--accent-amber)' : 'var(--accent-green)', marginBottom: '8px' }}>
              {error ? 'WHATSAPP ALERTS OPENED' : 'WHATSAPP ALERTS DISPATCHED!'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px' }}>
              {error
                ? 'WhatsApp opened for each contact. Tap Send in each WhatsApp window to deliver the alert.'
                : `Emergency WhatsApp messages sent to ${sosResponse?.contacts?.length || displayWaLinks.length} trusted contacts with live GPS location.`}
            </p>

            {error && (
              <div style={{ background: 'rgba(255, 149, 0, 0.1)', border: '1px solid rgba(255, 149, 0, 0.3)', padding: '12px', borderRadius: '10px', marginBottom: '16px', textAlign: 'left' }}>
                <p style={{ fontSize: '12px', color: 'var(--accent-amber)' }}>{error}</p>
              </div>
            )}

            {/* Location Details */}
            <div style={{ background: 'var(--bg-input)', padding: '16px', borderRadius: '12px', textAlign: 'left', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-primary)', marginBottom: '6px' }}>
                <MapPin style={{ width: '16px', height: '16px', color: 'var(--accent-cyan)' }} />
                <span>{locationName}</span>
              </div>
              <div style={{ fontFamily: 'monospace', fontSize: '12px', color: 'var(--accent-cyan)', marginBottom: '8px', paddingLeft: '24px' }}>
                Exact GPS: {latitude.toFixed(6)}, {longitude.toFixed(6)}
              </div>
              <div style={{ paddingLeft: '24px' }}>
                <a
                  href={`https://www.openstreetmap.org/?mlat=${latitude.toFixed(6)}&mlon=${longitude.toFixed(6)}#map=18/${latitude.toFixed(6)}/${longitude.toFixed(6)}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{ color: 'var(--accent-green)', fontSize: '12px', fontWeight: '700', textDecoration: 'none' }}
                >
                  🗺️ Live OpenStreetMap Link ↗
                </a>
              </div>
            </div>

            {/* WhatsApp Contact Buttons */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
              <p style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-secondary)', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                <MessageCircle style={{ width: '14px', height: '14px', display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} />
                WhatsApp Emergency Contacts
              </p>
              {displayWaLinks.map((wa, idx) => (
                <a
                  key={idx}
                  href={wa.wa_link}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 16px',
                    borderRadius: '12px',
                    background: 'rgba(37, 211, 102, 0.1)',
                    border: '1px solid rgba(37, 211, 102, 0.3)',
                    textDecoration: 'none',
                    transition: 'all 0.2s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(37, 211, 102, 0.2)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(37, 211, 102, 0.1)'}
                >
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    background: '#25D366',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <MessageCircle style={{ width: '18px', height: '18px', color: '#fff' }} />
                  </div>
                  <div style={{ flex: 1, textAlign: 'left' }}>
                    <p style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>{wa.name}</p>
                    <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{wa.phone}</p>
                  </div>
                  <span style={{ fontSize: '12px', fontWeight: '700', color: '#25D366' }}>
                    Send via WhatsApp →
                  </span>
                </a>
              ))}
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '12px' }}>
              {error && (
                <button
                  onClick={handleRetry}
                  style={{
                    flex: 1,
                    padding: '12px',
                    borderRadius: '12px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--accent-amber)',
                    color: 'var(--accent-amber)',
                    fontWeight: '700',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  <RefreshCw style={{ width: '16px', height: '16px' }} />
                  Retry
                </button>
              )}
              <button
                onClick={handleCancel}
                className="gradient-btn"
                style={{ flex: 1, padding: '12px' }}
              >
                Close Window
              </button>
            </div>
        </>
      </div>
    </div>
  );
};

export default SosModal;
