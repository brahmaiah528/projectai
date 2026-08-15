import axios from 'axios';

// Dynamic API Base URL:
// - If VITE_API_URL is provided (Production/Render/Vercel), uses ${VITE_API_URL}/api (without trailing slashes)
// - If VITE_API_URL is undefined (Local Development), falls back to '/api' (proxied by Vite)
const rawBaseUrl = import.meta.env.VITE_API_URL;
const baseURL = rawBaseUrl
  ? `${rawBaseUrl.replace(/\/+$/, '')}/api`
  : '/api';

const API = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to attach JWT token
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

// Response interceptor: simply pass through errors to components without forced page redirects
API.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);

export default API;
