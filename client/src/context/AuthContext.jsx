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

  const googleLogin = () => {
    return new Promise(async (resolve, reject) => {
      try {
        const res = await API.get('/auth/google/login-url');
        if (!res.data.available || !res.data.auth_url) {
          reject(new Error(res.data.message || 'Google Sign-In not configured.'));
          return;
        }
        const popup = window.open(res.data.auth_url, 'GoogleLogin', 'width=600,height=700,top=100,left=300');
        let isHandled = false;

        const handler = (event) => {
          if (event.data && (event.data.type === 'GOOGLE_LOGIN_SUCCESS' || event.data.type === 'GMAIL_CONNECTED' || event.data.token)) {
            const { token: jwtToken, user: userData, error } = event.data;
            if (error) { 
              isHandled = true;
              window.removeEventListener('message', handler);
              reject(new Error(error)); 
              return; 
            }
            if (jwtToken && userData) {
              isHandled = true;
              window.removeEventListener('message', handler);
              setToken(jwtToken);
              setUser(userData);
              localStorage.setItem('token', jwtToken);
              localStorage.setItem('user', JSON.stringify(userData));
              resolve(userData);
            }
          }
        };

        window.addEventListener('message', handler);

        // Cleanup if popup closed
        const timer = setInterval(() => {
          if (popup && popup.closed) {
            clearInterval(timer);
            window.removeEventListener('message', handler);
            if (!isHandled) {
              // Check if OAuth stored a fresh token in google_oauth_token key
              const googleToken = localStorage.getItem('google_oauth_token');
              const googleUser = localStorage.getItem('google_oauth_user');
              if (googleToken && googleUser) {
                const parsedUser = JSON.parse(googleUser);
                localStorage.setItem('token', googleToken);
                localStorage.setItem('user', googleUser);
                localStorage.removeItem('google_oauth_token');
                localStorage.removeItem('google_oauth_user');
                setToken(googleToken);
                setUser(parsedUser);
                resolve(parsedUser);
              } else {
                reject(new Error('Sign-in popup was closed.'));
              }
            }
          }
        }, 500);
      } catch (err) {
        reject(err);
      }
    });
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
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
