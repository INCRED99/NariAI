import React, { createContext, useContext, useState, useEffect } from 'react';
import client from '../api/client';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUserState] = useState(() => {
    try {
      const cached = localStorage.getItem('nari_user_profile');
      return cached ? JSON.parse(cached) : null;
    } catch (e) {
      return null;
    }
  });
  const [token, setToken] = useState(() => localStorage.getItem('nari_token') || null);
  const [loading, setLoading] = useState(true);

  const setUser = (newUser) => {
    setUserState(newUser);
    try {
      if (newUser) {
        localStorage.setItem('nari_user_profile', JSON.stringify(newUser));
      } else {
        localStorage.removeItem('nari_user_profile');
      }
    } catch (e) {
      // ignore
    }
  };

  useEffect(() => {
    const storedToken = localStorage.getItem('nari_token');
    if (!storedToken) {
      setUser(null);
      setToken(null);
      setLoading(false);
      return;
    }

    // Verify token with backend
    client.get('/profile')
      .then((res) => {
        const profileData = res.data?.profile || res.data;
        if (profileData && (profileData.name || profileData.email || profileData.uid)) {
          // Merge with any existing contacts from cache if backend returned empty array
          setUser((prev) => {
            const mergedContacts = (profileData.emergency_contacts && profileData.emergency_contacts.length > 0)
              ? profileData.emergency_contacts
              : (prev?.emergency_contacts || []);
            return {
              ...prev,
              ...profileData,
              emergency_contacts: mergedContacts
            };
          });
          setToken(storedToken);
        }
      })
      .catch((err) => {
        console.warn('Authentication token verification notice:', err?.message);
        // Only clear session if backend explicitly responds with 401 Unauthorized
        if (err.response?.status === 401) {
          localStorage.removeItem('nari_token');
          localStorage.removeItem('nari_user_profile');
          setToken(null);
          setUserState(null);
        }
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = async (email, password) => {
    try {
      const res = await client.post('/auth/login', { email, password });
      const authToken = res.data.token || res.data.idToken;
      if (authToken) {
        localStorage.setItem('nari_token', authToken);
        setToken(authToken);
        const profile = res.data.profile || { name: res.data.name || email, email, uid: res.data.uid };
        setUser(profile);
        return { success: true };
      } else {
        throw new Error('Authentication succeeded but no security token was returned.');
      }
    } catch (err) {
      // Strictly do not create fallback/demo tokens
      localStorage.removeItem('nari_token');
      setToken(null);
      setUser(null);
      const message = err.response?.data?.detail || err.message || 'Login failed. Please verify your email and password.';
      throw new Error(message);
    }
  };

  const register = async (email, password, name, phone = '') => {
    try {
      const res = await client.post('/auth/register', { email, password, name, phone });
      const authToken = res.data.token || res.data.idToken;
      if (authToken) {
        localStorage.setItem('nari_token', authToken);
        setToken(authToken);
        setUser({ name, email, uid: res.data.uid });
        return { success: true };
      } else {
        // Log in immediately to get token
        return await login(email, password);
      }
    } catch (err) {
      // Strictly do not create fallback/demo tokens
      localStorage.removeItem('nari_token');
      setToken(null);
      setUser(null);
      const message = err.response?.data?.detail || err.message || 'Registration failed. Please try again.';
      throw new Error(message);
    }
  };

  const logout = () => {
    localStorage.removeItem('nari_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
