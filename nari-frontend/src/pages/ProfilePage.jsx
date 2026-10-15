import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';
import { User, Shield, Phone, Key, Plus, Trash2, Save, Globe } from 'lucide-react';

const ProfilePage = () => {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [safeWord, setSafeWord] = useState(user?.safe_word || 'Blue Moon');
  const [lang, setLang] = useState(user?.preferred_language || 'English (US)');
  const [contacts, setContacts] = useState(user?.emergency_contacts || []);
  const [savedMsg, setSavedMsg] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      if (user.name) setName(user.name);
      if (user.email) setEmail(user.email);
      if (user.phone) setPhone(user.phone);
      if (user.safe_word) setSafeWord(user.safe_word);
      if (user.preferred_language) setLang(user.preferred_language);
      if (user.emergency_contacts) setContacts(user.emergency_contacts);
    }
  }, [user]);

  const [newContactName, setNewContactName] = useState('');
  const [newContactRelation, setNewContactRelation] = useState('');
  const [newContactPhone, setNewContactPhone] = useState('');

  const handleAddContact = (e) => {
    e.preventDefault();
    if (!newContactName || !newContactPhone) return;
    const updated = [...contacts, { name: newContactName, relation: newContactRelation || 'Contact', phone: newContactPhone }];
    setContacts(updated);
    setNewContactName('');
    setNewContactRelation('');
    setNewContactPhone('');
  };

  const handleRemoveContact = (index) => {
    setContacts(contacts.filter((_, i) => i !== index));
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    const updatedProfile = {
      ...user,
      name,
      email,
      phone,
      safe_word: safeWord,
      preferred_language: lang,
      emergency_contacts: contacts
    };

    try {
      await client.post('/profile', {
        name,
        phone,
        preferred_language: lang,
        safe_word: safeWord,
        emergency_contacts: contacts
      });
      setUser(updatedProfile);
      setSavedMsg('Profile updated successfully!');
    } catch (err) {
      console.warn('Profile save note:', err);
      setUser(updatedProfile);
      setSavedMsg('Profile saved locally.');
    } finally {
      setSaving(false);
      setTimeout(() => setSavedMsg(''), 3000);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px', paddingBottom: '40px' }}>
      
      <div className="glass-panel" style={{ padding: '28px' }}>
        <h3 style={{ fontSize: '20px', fontWeight: '700', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <User style={{ color: 'var(--accent-purple)', width: '22px', height: '22px' }} />
          User Profile & Emergency Contacts
        </h3>

        {savedMsg && (
          <div style={{ padding: '10px 14px', borderRadius: '10px', background: 'rgba(52, 199, 89, 0.15)', color: 'var(--accent-green)', fontSize: '13px', fontWeight: '600', marginBottom: '20px' }}>
            {savedMsg}
          </div>
        )}

        <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Full Name</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="glass-input" style={{ width: '100%' }} />
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Email Address</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="glass-input" style={{ width: '100%' }} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Phone Number</label>
              <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} className="glass-input" style={{ width: '100%' }} />
            </div>

            <div>
              <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Preferred Language</label>
              <select value={lang} onChange={(e) => setLang(e.target.value)} className="glass-input" style={{ width: '100%' }}>
                <option value="English (US)">English (US)</option>
                <option value="Hindi">Hindi (हिंदी)</option>
                <option value="Bengali">Bengali (বাংলা)</option>
                <option value="Tamil">Tamil (தமிழ்)</option>
                <option value="Spanish">Spanish</option>
              </select>
            </div>
          </div>

          {/* Safe Word Settings */}
          <div style={{ padding: '20px', borderRadius: '12px', background: 'var(--bg-input)', border: '1px solid var(--border-color)' }}>
            <label style={{ fontSize: '13px', fontWeight: '700', color: 'var(--accent-purple)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <Key style={{ width: '16px', height: '16px' }} />
              Active Emergency Safe Word
            </label>
            <input type="text" value={safeWord} onChange={(e) => setSafeWord(e.target.value)} className="glass-input" style={{ width: '100%', marginTop: '6px', fontWeight: '700', fontSize: '15px' }} />
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }}>
              When spoken or typed into Nari AI, this triggers an immediate silent location broadcast.
            </p>
          </div>

          <button type="submit" className="gradient-btn" style={{ width: '100%', padding: '14px', marginTop: '8px' }}>
            <Save style={{ width: '18px', height: '18px' }} />
            Save Profile & Safe Word
          </button>

        </form>
      </div>

      {/* Emergency Contacts Management */}
      <div className="glass-panel" style={{ padding: '28px' }}>
        <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Phone style={{ color: 'var(--accent-cyan)', width: '20px', height: '20px' }} />
          Manage Emergency Contacts
        </h3>

        {/* Existing Contacts List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
          {contacts.map((c, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 18px', borderRadius: '12px', background: 'var(--bg-input)' }}>
              <div>
                <p style={{ fontSize: '14px', fontWeight: '700', color: 'var(--text-primary)' }}>{c.name}</p>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{c.relation} • {c.phone}</p>
              </div>
              <button onClick={() => handleRemoveContact(i)} style={{ background: 'transparent', border: 'none', color: 'var(--accent-red)', cursor: 'pointer', padding: '6px' }}>
                <Trash2 style={{ width: '18px', height: '18px' }} />
              </button>
            </div>
          ))}
        </div>

        {/* Add New Contact Form */}
        <form onSubmit={handleAddContact} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: '12px', alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Contact Name</label>
            <input type="text" placeholder="e.g. Rahul" value={newContactName} onChange={(e) => setNewContactName(e.target.value)} className="glass-input" style={{ width: '100%' }} />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Relation</label>
            <input type="text" placeholder="e.g. Brother" value={newContactRelation} onChange={(e) => setNewContactRelation(e.target.value)} className="glass-input" style={{ width: '100%' }} />
          </div>
          <div>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Phone Number</label>
            <input type="text" placeholder="+91 98765..." value={newContactPhone} onChange={(e) => setNewContactPhone(e.target.value)} className="glass-input" style={{ width: '100%' }} />
          </div>
          <button type="submit" className="gradient-btn" style={{ padding: '12px 18px' }}>
            <Plus style={{ width: '18px', height: '18px' }} />
          </button>
        </form>
      </div>

    </div>
  );
};

export default ProfilePage;
