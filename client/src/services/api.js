import axios from 'axios';

// Dynamic API Base URL:
// - If VITE_API_URL is provided (Production/Render/Vercel), uses ${VITE_API_URL}/api (without trailing slashes)
// - If VITE_API_URL is undefined (Local Development), falls back to '/api' (proxied by Vite)
const rawBaseUrl = import.meta.env.VITE_API_URL;
const baseURL = (rawBaseUrl && rawBaseUrl.startsWith('http') && !rawBaseUrl.includes('localhost:5001'))
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

// Response interceptor: ONLY clear session on explicit token-invalid/expired 401 from server.
// Do NOT logout on other 401s (e.g. feature-gated endpoints, Google not linked, etc.)
API.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const msg = (error?.response?.data?.message || '').toLowerCase();
    const isAuthRoute = error?.config?.url?.includes('/auth/login') || error?.config?.url?.includes('/auth/register');

    // Only force-logout when server explicitly says the JWT token itself is invalid/expired
    const isTokenInvalid = status === 401 && (
      msg.includes('token has expired') ||
      msg.includes('invalid token') ||
      msg.includes('signature verification failed') ||
      msg.includes('token is invalid')
    );

    if (!isAuthRoute && isTokenInvalid) {
      console.warn('[API Interceptor] JWT token expired/invalid — clearing session.');
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default API;
