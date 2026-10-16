import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, Mic, AlertTriangle, Shield, Paperclip, CheckCircle } from 'lucide-react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';
import ThreatGauge from '../components/ThreatGauge';

const ChatPage = ({ onTriggerSos }) => {
  const { user } = useAuth();
  const userName = user?.name ? user.name.split(' ')[0] : 'there';
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: `Hello ${userName}! I'm Nari, your real-time safety companion. I monitor your surroundings and conversation for distress signals. How can I assist you right now?`
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeState, setActiveState] = useState('Normal');
  const [threatScore, setThreatScore] = useState(15);
  const [nextAction, setNextAction] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const query = textToSend || input;
    if (!query.trim() || loading) return;

    const userMsg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    // ── CLIENT-SIDE SAFE WORD CHECK ──────────────────────────────────────────
    // Synchronous check inside the click/submit handler — WhatsApp opens
    // immediately, before any async API call, to avoid popup blocker.
    const safeWord = (user?.safe_word || 'blue moon').toLowerCase().trim();
    if (safeWord.length >= 3 && query.toLowerCase().includes(safeWord)) {
      setActiveState('Emergency');
      setThreatScore(100);
      onTriggerSos(`🔑 SAFE WORD "${user?.safe_word || 'Blue Moon'}" detected in message`);
    }
    // ─────────────────────────────────────────────────────────────────────────

    try {
      // Format chat history for API payload
      const historyFormatted = messages.map(m => ({ role: m.role, content: m.content }));

      const res = await client.post('/chat', {
        history: historyFormatted,
        user_message: query,
        user_id: user?.uid || user?.email || 'user'
      });

      const { reply, state, next_action, is_emergency, threat_score } = res.data;

      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
      setActiveState(state || 'Normal');
      if (threat_score !== undefined) setThreatScore(threat_score);
      if (next_action) setNextAction(next_action);

      if (threat_score >= 100 || is_emergency) {
        onTriggerSos(`Risk level 100% critical — ${state || 'Emergency'} state detected in conversation`);
      }
    } catch (err) {
      console.error('Chat processing error:', err);
      let errorReply = `⚠️ Connection error: Unable to reach Nari LLM service. (${err.message || 'Server error'})`;
      if (query.toLowerCase().includes('blue moon') || (user?.safe_word && query.toLowerCase().includes(user.safe_word.toLowerCase()))) {
        errorReply = "🚨 SAFE WORD DETECTED! Activating immediate location broadcast & alerting trusted contacts.";
        setActiveState('Emergency');
        setThreatScore(100);
      }
      setMessages((prev) => [...prev, { role: 'assistant', content: errorReply }]);
    } finally {
      setLoading(false);
    }
  };

  // Instant trigger as soon as user types the complete safe word into input
  const handleInputChange = (e) => {
    const val = e.target.value;
    setInput(val);
    const safeWord = (user?.safe_word || 'blue moon').toLowerCase().trim();
    if (safeWord.length >= 3 && val.toLowerCase().includes(safeWord)) {
      setInput('');
      setActiveState('Emergency');
      setThreatScore(100);
      onTriggerSos(`🔑 SAFE WORD "${user?.safe_word || 'Blue Moon'}" typed in chat input`);
    }
  };

  const quickChips = [
    "I am walking home alone at night",
    "A car is following me slowly",
    "What is my safe word?",
    "Give me safety tips for public transit"
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: '24px', height: 'calc(100vh - 120px)' }}>
      
      {/* Main Chat Interface */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        
        {/* Chat Header Banner */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: activeState === 'Emergency' ? 'rgba(255, 59, 48, 0.15)' : activeState === 'Warning' ? 'rgba(255, 149, 0, 0.15)' : 'var(--bg-input)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
              <Bot style={{ width: '22px', height: '22px' }} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '700' }}>Nari Safety AI Companion</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Grounded in Safety KB & Long-Term Memory</p>
            </div>
          </div>

          <div style={{
            padding: '6px 14px',
            borderRadius: '20px',
            fontWeight: '700',
            fontSize: '12px',
            background: activeState === 'Emergency' ? 'rgba(255, 59, 48, 0.2)' : activeState === 'Warning' ? 'rgba(255, 149, 0, 0.2)' : 'rgba(52, 199, 89, 0.2)',
            color: activeState === 'Emergency' ? 'var(--accent-red)' : activeState === 'Warning' ? 'var(--accent-amber)' : 'var(--accent-green)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor' }} />
            {activeState.toUpperCase()} STATE
          </div>
        </div>

        {/* Message Log */}
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                gap: '12px'
              }}
            >
              {msg.role === 'assistant' && (
                <div style={{ width: '32px', height: '32px', borderRadius: '10px', background: 'var(--primary-gradient)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', flexShrink: 0 }}>
                  <Bot style={{ width: '18px', height: '18px' }} />
                </div>
              )}
              <div style={{
                maxWidth: '75%',
                padding: '14px 18px',
                borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                background: msg.role === 'user' ? 'var(--primary-gradient)' : 'var(--bg-input)',
                color: '#ffffff',
                fontSize: '14px',
                lineHeight: '1.5',
                border: msg.role === 'user' ? 'none' : '1px solid var(--border-color)',
                boxShadow: msg.role === 'user' ? 'var(--shadow-glow)' : 'none'
              }}>
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div style={{ display: 'flex', gap: '8px', padding: '12px 18px', background: 'var(--bg-input)', borderRadius: '14px', width: 'fit-content' }}>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Analyzing response...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div style={{ padding: '0 24px 12px 24px', display: 'flex', gap: '8px', overflowX: 'auto' }}>
          {quickChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(chip)}
              style={{
                whiteSpace: 'nowrap',
                padding: '8px 14px',
                borderRadius: '20px',
                background: 'var(--bg-input)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              {chip}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} style={{ padding: '16px 24px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: '12px' }}>
          <input
            type="text"
            placeholder="Type your message or say your safe word..."
            value={input}
            onChange={handleInputChange}
            className="glass-input"
            style={{ flex: 1 }}
          />
          <button type="submit" className="gradient-btn" disabled={loading} style={{ padding: '12px 20px' }}>
            <Send style={{ width: '18px', height: '18px' }} />
          </button>
        </form>
      </div>

      {/* Right Sidebar: Threat & Context Panel */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Threat Gauge */}
        <div className="glass-panel" style={{ padding: '24px', textAlign: 'center' }}>
          <h4 style={{ fontSize: '15px', fontWeight: '700', marginBottom: '12px' }}>Active Risk Score</h4>
          <ThreatGauge score={threatScore} state={activeState} />
        </div>

        {/* Next Action Box */}
        {nextAction && (
          <div className="glass-panel" style={{ padding: '20px', background: 'rgba(255, 59, 48, 0.1)', border: '1px solid rgba(255, 59, 48, 0.3)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-red)', fontWeight: '700', fontSize: '13px', marginBottom: '6px' }}>
              <AlertTriangle style={{ width: '16px', height: '16px' }} />
              Recommended Action
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{nextAction}</p>
          </div>
        )}

        {/* Safe Word Info */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-purple)', fontWeight: '700', fontSize: '13px', marginBottom: '8px' }}>
            <Shield style={{ width: '16px', height: '16px' }} />
            Active Safe Word
          </div>
          <p style={{ fontSize: '16px', fontWeight: '800', color: 'var(--text-primary)' }}>"Blue Moon"</p>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Including this phrase in any message immediately triggers silent emergency dispatch.
          </p>
        </div>

      </div>

    </div>
  );
};

export default ChatPage;
