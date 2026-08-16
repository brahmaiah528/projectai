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
  // If we already have both token and user cached, skip the loading state entirely
  const [isLoading, setIsLoading] = useState(() => {
    const hasToken = !!localStorage.getItem('token');
    const hasUser = !!localStorage.getItem('user');
    // If both are cached we can render immediately, no need to show loading
    return hasToken && !hasUser; // only show loading if token exists but no user yet
  });
  const verifyAttempts = useRef(0);

  // Run verification ONCE on mount only — never on subsequent state changes
  // This prevents re-verification (and potential logout) when switching categories etc.
  useEffect(() => {
    const verifyUser = async () => {
      const savedToken = localStorage.getItem('token');
      const savedUser = localStorage.getItem('user');

      // Both cached — render immediately, no network call needed
      if (savedToken && savedUser) {
        try {
          if (!user) setUser(JSON.parse(savedUser));
        } catch {}
        setIsLoading(false);
        return;
      }

      if (savedToken && !savedUser) {
        // Have token but no user data — verify with server once
        try {
          const res = await API.get('/auth/me');
          setUser(res.data.user);
          localStorage.setItem('user', JSON.stringify(res.data.user));
        } catch (err) {
          const status = err?.response?.status;
          const msg = (err?.response?.data?.message || '').toLowerCase();
          // Only clear session on explicit token invalid/expired
          if (status === 401 && (msg.includes('token has expired') || msg.includes('invalid token'))) {
            console.warn('[Auth] Token expired on startup — clearing session.');
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            setToken(null);
            setUser(null);
          }
          // Otherwise keep the user logged in — network errors are temporary
        }
      }
      setIsLoading(false);
    };
    verifyUser();
  }, []); // empty deps — only run once on mount, never on token/state changes

  const _clearSession = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const login = async (email, password, rememberMe) => {
    const res = await API.post('/auth/login', { email, password, remember_me: rememberMe });
    const { token: jwtToken, user: userData } = res.data;
    // Update state + localStorage first
    localStorage.setItem('token', jwtToken);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(jwtToken);
    setUser(userData);
    // Ensure isLoading is false so ProtectedRoute doesn't redirect back to login
    setIsLoading(false);
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
    localStorage.setItem('token', jwtToken);
    localStorage.setItem('user', JSON.stringify(userData));
    setToken(jwtToken);
    setUser(userData);
    setIsLoading(false);
    return res.data;
  };

  const logout = () => {
    // 1. Instantly wipe local session credentials
    _clearSession();
    // 2. Fire non-blocking logout notification to backend
    API.post('/auth/logout').catch(() => {});
    // 3. Hard redirect to /login to ensure clean state
    window.location.href = '/login';
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
