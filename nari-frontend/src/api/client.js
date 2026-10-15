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

// Proactively remove any legacy exposed key from localStorage
if (typeof window !== 'undefined' && window.localStorage) {
  try {
    localStorage.removeItem('nari_groq_key');
  } catch (e) {
    // ignore
  }
}

// Interceptor to inject stored Auth Token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('nari_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

export default client;
