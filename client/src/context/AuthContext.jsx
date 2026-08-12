import React, { createContext, useContext, useState, useEffect } from 'react';
import API from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('token') || null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const verifyUser = async () => {
      if (token && !user) {
        try {
          const res = await API.get('/auth/me');
          setUser(res.data.user);
          localStorage.setItem('user', JSON.stringify(res.data.user));
        } catch (err) {
          console.error("Session verification failed:", err);
          if (err.response && err.response.status === 401) {
            logout();
          }
        }
      }
      setIsLoading(false);
    };
    verifyUser();
  }, [token]);

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
   * 
   * Flow:
   *  1. Fetch the Google auth URL from the backend
   *  2. Store the current page in sessionStorage so we know where to redirect back
   *  3. Navigate the entire browser window to Google's OAuth page
   *  4. Google → Render backend → HTTP 302 → /auth/callback#token=...
   *  5. AuthCallbackPage reads token from URL fragment, stores it, navigates to /dashboard
   * 
   * No popup, no postMessage, no cross-origin issues.
   */
  const googleLogin = async () => {
    const res = await API.get('/auth/google/login-url');
    if (!res.data.available || !res.data.auth_url) {
      throw new Error(res.data.message || 'Google Sign-In not configured on this server.');
    }
    // Mark that a Google login is in progress (AuthCallbackPage checks this)
    sessionStorage.setItem('google_login_pending', '1');
    // Full page redirect — browser navigates away, comes back to /auth/callback
    window.location.href = res.data.auth_url;
    // The function never returns after this line (page navigates away)
    // Return a promise that never resolves so callers don't see errors
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

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
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
