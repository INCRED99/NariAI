import React, { useState, useEffect, useCallback } from 'react';
import { AlertTriangle, PhoneCall, MapPin, X, CheckCircle, RefreshCw, AlertCircle, MessageCircle } from 'lucide-react';
import client from '../api/client';
import { useLocation } from '../context/LocationContext';
import { useAuth } from '../context/AuthContext';

const SosModal = ({ isOpen, onClose }) => {
  const [countdown, setCountdown] = useState(5);
  const [isSent, setIsSent] = useState(false);
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

  useEffect(() => {
    let timer;
    if (isOpen && countdown > 0 && !isSent && !error) {
      timer = setInterval(() => {
        setCountdown((prev) => prev - 1);
      }, 1000);
    } else if (isOpen && countdown === 0 && !isSent && !loading && !error) {
      triggerSos();
    }
    return () => clearInterval(timer);
  }, [isOpen, countdown, isSent, loading, error]);

  const triggerSos = async () => {
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
        setIsSent(true);

        // Auto-open WhatsApp for each contact
        if (res.data.whatsapp_links && res.data.whatsapp_links.length > 0) {
          openWhatsAppForContacts(res.data.whatsapp_links);
        }
      } else {
        setError('Server returned unsuccessful response.');
        setIsSent(true);
        openWhatsAppFallback();
      }
    } catch (err) {
      console.error('SOS dispatch error:', err);
      const errMsg = err.response?.data?.detail || err.message || 'Unknown error';
      setError(`SOS backend issue: ${errMsg}`);
      setIsSent(true);
      // Fallback: open WhatsApp locally even if backend is down
      openWhatsAppFallback();
    } finally {
      setLoading(false);
    }
  };

  // Fallback: generate wa.me links locally and open WhatsApp
  const openWhatsAppFallback = useCallback(() => {
    const emergencyMsg = buildEmergencyMessage();
    const contacts = user?.emergency_contacts || [
      { name: 'Aarav Sharma', phone: '7007914594' },
      { name: 'Neha Verma', phone: '+91 91234 56789' }
    ];

    contacts.forEach((c, idx) => {
      const waLink = generateLocalWaLink(c.phone, `🚨 SOS for ${c.name}!\n\n${emergencyMsg}`);
      setTimeout(() => {
        window.open(waLink, '_blank');
      }, idx * 800);
    });
    setWaOpened(true);
  }, [user, buildEmergencyMessage, generateLocalWaLink]);

  const handleRetry = () => {
    setError(null);
    setIsSent(false);
    setSosResponse(null);
    setWaOpened(false);
    setCountdown(0);
  };

  const handleCancel = () => {
    setCountdown(5);
    setIsSent(false);
    setError(null);
    setSosResponse(null);
    setWaOpened(false);
    onClose();
  };

  if (!isOpen) return null;

  // Derive contact names from response or user profile
  const contactNames = sosResponse?.contacts?.map(c => c.name).join(' & ')
    || user?.emergency_contacts?.map(c => c.name).join(' & ')
    || 'Aarav Sharma & Neha Verma';

  // Build WhatsApp links for display (from backend response or local fallback)
  const displayWaLinks = sosResponse?.whatsapp_links?.length > 0
    ? sosResponse.whatsapp_links
    : (user?.emergency_contacts || [
        { name: 'Aarav Sharma', phone: '7007914594' },
        { name: 'Neha Verma', phone: '+91 91234 56789' }
      ]).map(c => ({
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
        {!isSent ? (
          <>
            <div style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              background: 'var(--emergency-gradient)',
              margin: '0 auto 20px auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 35px rgba(255, 59, 48, 0.6)'
            }} className="pulse-emergency">
              <AlertTriangle style={{ width: '40px', height: '40px', color: '#fff' }} />
            </div>

            <h3 style={{ fontSize: '24px', fontWeight: '800', color: '#FF3B30', marginBottom: '8px' }}>
              EMERGENCY SOS TRIGGERED
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '12px' }}>
              Sending WhatsApp alerts with live GPS to emergency contacts in:
            </p>

            <div style={{
              background: 'var(--bg-input)',
              padding: '8px 14px',
              borderRadius: '10px',
              marginBottom: '20px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontFamily: 'monospace',
              fontSize: '13px',
              color: 'var(--accent-cyan)'
            }}>
              <MapPin style={{ width: '14px', height: '14px' }} />
              <span>{latitude.toFixed(6)}, {longitude.toFixed(6)}</span>
            </div>

            <div style={{
              fontSize: '54px',
              fontWeight: '900',
              color: '#FF3B30',
              marginBottom: '28px',
              fontFamily: 'monospace'
            }}>
              00:0{countdown}
            </div>

            <button
              onClick={handleCancel}
              style={{
                width: '100%',
                padding: '14px',
                borderRadius: '12px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-primary)',
                fontWeight: '700',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              <X style={{ width: '18px', height: '18px' }} />
              CANCEL EMERGENCY (FALSE ALARM)
            </button>
          </>
        ) : (
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
        )}
      </div>
    </div>
  );
};

export default SosModal;
