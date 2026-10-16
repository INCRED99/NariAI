import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Mic, MicOff, Send, ShieldAlert, CheckCircle2, RotateCcw, User, ExternalLink } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLocation } from '../context/LocationContext';
import client from '../api/client';
import { openWhatsAppNow, buildSosMessage, cleanPhone } from '../utils/emergencyWhatsapp';

const EmergencyPage = () => {
  const { user } = useAuth();
  const { latitude, longitude, locationName } = useLocation();

  const [chatMessages, setChatMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [lastDispatchedTime, setLastDispatchedTime] = useState(null);

  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const inputRef = useRef(null);
  const liveTranscriptRef = useRef('');
  const hasSentVoiceRef = useRef(false);

  // Get emergency contacts — no fallback data, only use what user has set
  const contacts = (user?.emergency_contacts?.length > 0) ? user.emergency_contacts : [];
  const firstContact = contacts[0] || null;

  // Scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, liveTranscript]);

  // Helper: clean phone number
  const formatPhone = (phone) => cleanPhone(phone);

  // Immediately open WhatsApp to first contact — aborts silently if no contact set
  const openWhatsAppImmediately = useCallback((situationText) => {
    if (!firstContact?.phone) return;
    const message = buildSosMessage(situationText, { latitude, longitude, locationName });
    openWhatsAppNow(firstContact.phone, message);
  }, [firstContact, latitude, longitude, locationName]);

  // Central dispatch: opens WhatsApp instantly & logs incident to backend asynchronously
  const sendAlert = useCallback((situationText) => {
    const text = situationText.trim();
    if (!text) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. IMMEDIATELY open WhatsApp (no-op if no contact set)
    openWhatsAppImmediately(text);

    // 2. Add user message + system confirmation to chat stream
    const systemMsg = firstContact
      ? `⚡ WhatsApp opened & distress alert dispatched to ${firstContact.name || 'Emergency Contact'} (${firstContact.phone || ''}) with live location.`
      : `⚠️ No emergency contact set — please add one in My Profile to enable WhatsApp dispatch.`;

    setChatMessages(prev => [
      ...prev,
      { role: 'user', text, time: timeStr },
      { role: 'system', text: systemMsg, time: timeStr },
    ]);

    setLastDispatchedTime(timeStr);

    // 3. Fire backend logging in the background (non-blocking)
    client.post('/sos', {
      situation: text,
      latitude,
      longitude,
      location_name: locationName,
      trigger_type: 'Emergency Chat SOS',
      user_id: user?.uid || user?.email || 'user',
    }).catch(err => {
      console.warn('Backend SOS log error (WhatsApp already opened):', err);
    });
  }, [openWhatsAppImmediately, firstContact, latitude, longitude, locationName, user]);

  // Handle typing input changes (detects safe word immediately on keystroke)
  const handleInputChange = (e) => {
    const val = e.target.value;
    setInputText(val);
    const safeWord = (user?.safe_word || 'blue moon').toLowerCase().trim();
    if (safeWord.length >= 3 && val.toLowerCase().includes(safeWord)) {
      setInputText('');
      sendAlert(`🔑 SAFE WORD "${user?.safe_word || 'Blue Moon'}" detected in message`);
    }
  };

  // Handle typing send
  const handleSendText = (e) => {
    e?.preventDefault();
    const text = inputText.trim();
    if (!text) return;

    setInputText('');
    const safeWord = (user?.safe_word || 'blue moon').toLowerCase().trim();
    const situation = (safeWord.length >= 3 && text.toLowerCase().includes(safeWord))
      ? `🔑 SAFE WORD "${user?.safe_word || 'Blue Moon'}" detected: ${text}`
      : text;
    sendAlert(situation);

    // Refocus input
    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  };

  // Handle quick phrases
  const handleQuickSend = (phrase) => {
    sendAlert(phrase);
  };

  // Start voice recognition
  const startListening = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setChatMessages(prev => [
        ...prev,
        {
          role: 'system',
          text: '⚠️ Speech recognition is not supported in this browser.',
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
      return;
    }

    // Reset voice transcript refs
    liveTranscriptRef.current = '';
    hasSentVoiceRef.current = false;
    setLiveTranscript('');

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;

    let finalTranscript = '';

    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interim += transcript;
        }
      }
      const combined = (finalTranscript + interim).trim();
      liveTranscriptRef.current = combined;
      setLiveTranscript(combined);

      // Real-time voice safe word detection
      const safeWord = (user?.safe_word || 'blue moon').toLowerCase().trim();
      if (safeWord.length >= 3 && combined.toLowerCase().includes(safeWord) && !hasSentVoiceRef.current) {
        hasSentVoiceRef.current = true;
        try {
          recognition.stop();
        } catch (err) {}
        setIsListening(false);
        setLiveTranscript('');
        sendAlert(`🔑 SAFE WORD "${user?.safe_word || 'Blue Moon'}" spoken: "${combined}"`);
      }
    };

    recognition.onerror = (event) => {
      console.warn('Speech recognition status:', event.error);
      setIsListening(false);
      // If error or stopped with captured speech, auto-send immediately
      if (!hasSentVoiceRef.current && liveTranscriptRef.current.trim()) {
        hasSentVoiceRef.current = true;
        const speech = liveTranscriptRef.current.trim();
        setLiveTranscript('');
        sendAlert(`🎙️ Voice: "${speech}"`);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      // When listener automatically ends (e.g. silence), immediately send if not sent yet
      if (!hasSentVoiceRef.current && liveTranscriptRef.current.trim()) {
        hasSentVoiceRef.current = true;
        const speech = liveTranscriptRef.current.trim();
        setLiveTranscript('');
        sendAlert(`🎙️ Voice: "${speech}"`);
      }
    };

    recognitionRef.current = recognition;
    try {
      recognition.start();
      setIsListening(true);
    } catch (e) {
      console.error('Recognition start error:', e);
    }
  };

  // Stop voice recognition -> IMMEDIATELY send & open WhatsApp
  const stopListening = () => {
    setIsListening(false);
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.warn(e);
      }
    }

    if (!hasSentVoiceRef.current) {
      hasSentVoiceRef.current = true;
      const speech = liveTranscriptRef.current.trim();
      const alertMsg = speech ? `🎙️ Voice: "${speech}"` : '🎙️ Voice listener stopped — Emergency SOS!';
      setLiveTranscript('');
      // Synchronously triggered inside the user's click -> WhatsApp opens immediately without popup block!
      sendAlert(alertMsg);
    }
  };

  const handleClearChat = () => {
    setChatMessages([]);
    setInputText('');
    setLiveTranscript('');
    liveTranscriptRef.current = '';
    hasSentVoiceRef.current = false;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', paddingBottom: '40px', maxWidth: '720px', margin: '0 auto' }}>

      {/* Header */}
      <div className="glass-panel" style={{
        padding: '20px 24px',
        background: 'rgba(255, 59, 48, 0.08)',
        border: '1px solid rgba(255, 59, 48, 0.25)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <ShieldAlert style={{ width: '32px', height: '32px', color: 'var(--accent-red)', flexShrink: 0 }} />
          <div>
            <h3 style={{ fontSize: '18px', fontWeight: '800', color: 'var(--accent-red)', margin: 0 }}>
              Emergency Distress Hub
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Type or speak — WhatsApp opens immediately with your live GPS location.
            </p>
          </div>
        </div>

        {chatMessages.length > 0 && (
          <button
            onClick={handleClearChat}
            style={{
              padding: '6px 14px',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-muted)',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <RotateCcw style={{ width: '13px', height: '13px' }} />
            Clear
          </button>
        )}
      </div>

      {/* Target Contact Banner */}
      {firstContact ? (
        <div className="glass-panel" style={{
          padding: '14px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          background: 'rgba(37, 211, 102, 0.06)',
          border: '1px solid rgba(37, 211, 102, 0.25)',
        }}>
          <div style={{
            width: '40px', height: '40px', borderRadius: '50%',
            background: 'rgba(37, 211, 102, 0.2)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <User style={{ width: '20px', height: '20px', color: '#25D366' }} />
          </div>
          <div style={{ flex: 1 }}>
            <p style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
              {firstContact?.name || 'Emergency Contact'}
            </p>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
              {firstContact?.relation || 'Emergency Contact'} • +{cleanPhone(firstContact?.phone)}
            </p>
          </div>
          <div style={{
            padding: '4px 12px', borderRadius: '20px',
            background: 'rgba(37, 211, 102, 0.2)',
            fontSize: '11px', fontWeight: '700', color: '#25D366',
            display: 'flex', alignItems: 'center', gap: '5px'
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#25D366' }} />
            Instant WhatsApp Dispatch
          </div>
        </div>
      ) : (
        <div className="glass-panel" style={{
          padding: '16px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
          background: 'rgba(255, 149, 0, 0.08)',
          border: '1px solid rgba(255, 149, 0, 0.35)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '40px', height: '40px', borderRadius: '50%',
              background: 'rgba(255, 149, 0, 0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <User style={{ width: '20px', height: '20px', color: '#FF9500' }} />
            </div>
            <div>
              <p style={{ fontSize: '14px', fontWeight: '700', color: '#FF9500', margin: 0 }}>
                No emergency contact set
              </p>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
                Add a trusted contact to enable automated WhatsApp dispatch when SOS is triggered.
              </p>
            </div>
          </div>
          <Link
            to="/profile"
            className="gradient-btn"
            style={{ padding: '8px 16px', fontSize: '12px', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            Add Contact Now
          </Link>
        </div>
      )}

      {/* Chat Messages Area */}
      <div className="glass-panel" style={{
        padding: '20px',
        minHeight: '260px',
        maxHeight: '380px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}>
        {chatMessages.length === 0 && !isListening && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            <ShieldAlert style={{ width: '42px', height: '42px', opacity: 0.3, margin: '0 auto 12px auto', display: 'block' }} />
            <p style={{ fontSize: '14px', margin: 0, color: 'var(--text-primary)' }}>
              {firstContact ? (
                <>Ready to send emergency alert to <strong>{firstContact.name || 'Emergency Contact'}</strong>.</>
              ) : (
                <>Ready to send emergency alert to your emergency contact.</>
              )}
            </p>
            <p style={{ fontSize: '12px', marginTop: '6px', opacity: 0.7 }}>
              Type your message below or tap the microphone to speak. WhatsApp opens immediately.
            </p>
          </div>
        )}

        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              maxWidth: '85%',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              background: msg.role === 'user'
                ? 'linear-gradient(135deg, rgba(255, 59, 48, 0.2), rgba(255, 149, 0, 0.15))'
                : 'rgba(37, 211, 102, 0.12)',
              border: msg.role === 'user'
                ? '1px solid rgba(255, 59, 48, 0.35)'
                : '1px solid rgba(37, 211, 102, 0.3)',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              padding: '12px 16px',
            }}
          >
            <p style={{ fontSize: '14px', color: 'var(--text-primary)', margin: 0, lineHeight: 1.5 }}>
              {msg.text}
            </p>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
              {msg.time}
            </span>
          </div>
        ))}

        {/* Live speech recognition transcription indicator */}
        {isListening && (
          <div style={{
            maxWidth: '85%',
            alignSelf: 'flex-end',
            background: 'rgba(255, 59, 48, 0.1)',
            border: '1px dashed rgba(255, 59, 48, 0.5)',
            borderRadius: '16px 16px 4px 16px',
            padding: '12px 16px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <div style={{
                width: '10px', height: '10px', borderRadius: '50%', background: '#FF3B30',
                animation: 'pulse-dot 1s infinite',
              }} />
              <span style={{ fontSize: '11px', fontWeight: '800', color: '#FF3B30', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Listening... (Tap mic to stop & send instantly)
              </span>
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-primary)', margin: 0, fontStyle: 'italic' }}>
              {liveTranscript || 'Listening for your voice...'}
            </p>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input Form with Voice Button & Send */}
      <form onSubmit={handleSendText} style={{ display: 'flex', gap: '10px', alignItems: 'stretch' }}>
        {/* Voice Button */}
        <button
          type="button"
          onClick={isListening ? stopListening : startListening}
          style={{
            width: '52px',
            height: '52px',
            borderRadius: '14px',
            border: 'none',
            background: isListening
              ? 'linear-gradient(135deg, #FF3B30, #FF9500)'
              : 'rgba(122, 92, 255, 0.15)',
            color: isListening ? '#fff' : 'var(--accent-purple)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            transition: 'all 0.2s ease',
            boxShadow: isListening ? '0 0 24px rgba(255, 59, 48, 0.6)' : 'none',
            animation: isListening ? 'pulse-mic 1.2s infinite' : 'none',
          }}
          title={isListening ? 'Stop listener & send to WhatsApp immediately' : 'Start voice input'}
        >
          {isListening
            ? <MicOff style={{ width: '22px', height: '22px' }} />
            : <Mic style={{ width: '22px', height: '22px' }} />
          }
        </button>

        {/* Text Input */}
        <input
          ref={inputRef}
          type="text"
          value={inputText}
          onChange={handleInputChange}
          placeholder={isListening ? 'Listening to voice... Tap mic to stop & send' : 'Type your emergency message or safe word...'}
          disabled={isListening}
          style={{
            flex: 1,
            padding: '14px 18px',
            borderRadius: '14px',
            border: '1px solid var(--border-color)',
            background: 'var(--bg-input)',
            color: 'var(--text-primary)',
            fontSize: '14px',
            outline: 'none',
            transition: 'border-color 0.2s ease',
          }}
          onFocus={(e) => e.target.style.borderColor = 'var(--accent-purple)'}
          onBlur={(e) => e.target.style.borderColor = 'var(--border-color)'}
        />

        {/* Send Button */}
        <button
          type="submit"
          disabled={!inputText.trim() || isListening}
          style={{
            width: '52px',
            height: '52px',
            borderRadius: '14px',
            border: 'none',
            background: inputText.trim()
              ? 'var(--emergency-gradient)'
              : 'rgba(255, 255, 255, 0.05)',
            color: inputText.trim() ? '#fff' : 'var(--text-muted)',
            cursor: inputText.trim() ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            transition: 'all 0.2s ease',
          }}
          title="Send & Open WhatsApp immediately"
        >
          <Send style={{ width: '20px', height: '20px' }} />
        </button>
      </form>

      {/* Quick Phrases for 1-Tap SOS */}
      <div>
        <p style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>
          ⚡ 1-Tap Quick SOS
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {['Help!', 'Bachao!', 'Send Police', 'Someone is following me', 'I feel unsafe', 'Medical Emergency'].map((phrase) => (
            <button
              key={phrase}
              onClick={() => handleQuickSend(phrase)}
              style={{
                padding: '8px 16px',
                borderRadius: '20px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-input)',
                color: 'var(--text-primary)',
                fontSize: '13px',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 59, 48, 0.15)';
                e.currentTarget.style.borderColor = 'rgba(255, 59, 48, 0.4)';
                e.currentTarget.style.color = 'var(--accent-red)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--bg-input)';
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.color = 'var(--text-primary)';
              }}
            >
              {phrase}
            </button>
          ))}
        </div>
      </div>

      {/* Keyframe animations */}
      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.3; transform: scale(0.6); }
        }
        @keyframes pulse-mic {
          0%, 100% { transform: scale(1); box-shadow: 0 0 15px rgba(255, 59, 48, 0.5); }
          50% { transform: scale(1.06); box-shadow: 0 0 28px rgba(255, 59, 48, 0.85); }
        }
      `}</style>
    </div>
  );
};

export default EmergencyPage;
