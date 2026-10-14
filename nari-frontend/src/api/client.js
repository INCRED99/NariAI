import axios from 'axios';

// Base API Client pointing to FastAPI backend
// Strips trailing slashes to ensure paths append cleanly
const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const API_BASE_URL = rawBaseUrl.replace(/\/+$/, '');

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Accommodate Render free-tier cold starts (spins down after 15m of inactivity)
  timeout: 60000,
});

// Interceptor to inject stored Auth Token and API Key overrides
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('nari_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const DEFAULT_GROQ_KEY = import.meta.env.VITE_GROQ_API_KEY || '';
  let groqKey = localStorage.getItem('nari_groq_key');
  if (!groqKey || groqKey.startsWith('gsk_Mnoe')) {
    groqKey = DEFAULT_GROQ_KEY;
    if (groqKey) {
      localStorage.setItem('nari_groq_key', groqKey);
    }
  }

  if (groqKey) {
    config.headers['x-api-key'] = groqKey;
    config.headers['x-groq-key'] = groqKey;
    config.headers['x-gemini-key'] = groqKey;
  }

  return config;
}, (error) => Promise.reject(error));

export default client;
