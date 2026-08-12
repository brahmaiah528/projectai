import axios from 'axios';

// In production (Vercel), VITE_API_URL points to the Render backend.
// In local dev, falls back to '/api' which Vite proxies to localhost:5001.
const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

const API = axios.create({
  baseURL: BASE_URL,
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
