import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import API from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('user');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [isLoading, setIsLoading] = useState(true);
  const verifyAttempts = useRef(0);

  useEffect(() => {
    const verifyUser = async () => {
      if (token) {
        // If we already have user data in state/localStorage, skip network call
        if (user) {
          setIsLoading(false);
          return;
        }
        // Retry up to 3 times — handles Render cold starts (first request can be slow)
        let lastErr = null;
        for (let attempt = 0; attempt < 3; attempt++) {
          try {
            const res = await API.get('/auth/me');
            setUser(res.data.user);
            localStorage.setItem('user', JSON.stringify(res.data.user));
            verifyAttempts.current = 0;
            setIsLoading(false);
            return;
          } catch (err) {
            lastErr = err;
            const status = err?.response?.status;
            // Only logout on explicit 401 with an auth-failure message (not network errors)
            if (status === 401 && err?.response?.data?.message) {
              const msg = err.response.data.message.toLowerCase();
              // Only clear session if server explicitly says token is invalid/expired
              // Do NOT logout on "user not found" — that's a DB wipe, auto-healing handles it
              if (msg.includes('token has expired') || msg.includes('invalid token')) {
                console.warn('[Auth] Token expired — clearing session.');
                _clearSession();
                setIsLoading(false);
                return;
              }
            }
            // For network errors, 500s, or "user not found" — wait and retry
            if (attempt < 2) {
              await new Promise(r => setTimeout(r, 1500 * (attempt + 1)));
            }
          }
        }
        // After 3 retries — keep user logged in with cached data, just warn
        console.warn('[Auth] Could not verify session after 3 attempts. Using cached user data.', lastErr?.message);
        // Use cached user data from localStorage if available — don't kick user out
        const cached = localStorage.getItem('user');
        if (cached) {
          try { setUser(JSON.parse(cached)); } catch {}
        }
      }
      setIsLoading(false);
    };
    verifyUser();
  }, [token]);

  const _clearSession = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const login = async (email, password, rememberMe) => {
    const res = await API.post('/auth/login', { email, password, remember_me: rememberMe });
    const { token: jwtToken, user: userData } = res.data;
    setToken(jwtToken);
    setUser(userData);
    localStorage.setItem('token', jwtToken);
    localStorage.setItem('user', JSON.stringify(userData));
    return res.data;
  };

  /**
   * googleLogin — full-page redirect (most reliable cross-origin approach).
   */
  const googleLogin = async () => {
    const res = await API.get('/auth/google/login-url');
    if (!res.data.available || !res.data.auth_url) {
      throw new Error(res.data.message || 'Google Sign-In not configured on this server.');
    }
    sessionStorage.setItem('google_login_pending', '1');
    window.location.href = res.data.auth_url;
    return new Promise(() => {});
  };

  const register = async (name, email, password) => {
    const res = await API.post('/auth/register', { name, email, password });
    const { token: jwtToken, user: userData } = res.data;
    setToken(jwtToken);
    setUser(userData);
    localStorage.setItem('token', jwtToken);
    localStorage.setItem('user', JSON.stringify(userData));
    return res.data;
  };

  const logout = async () => {
    // Call backend to clear server-side session cache
    try {
      await API.post('/auth/logout');
    } catch {
      // Ignore errors — still clear client-side session
    }
    _clearSession();
  };

  const updateProfile = (updatedUser) => {
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
  };

  const setTokenAndUser = (jwtToken, userData) => {
    setToken(jwtToken);
    setUser(userData);
    localStorage.setItem('token', jwtToken);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        googleLogin,
        register,
        logout,
        updateProfile,
        setTokenAndUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
