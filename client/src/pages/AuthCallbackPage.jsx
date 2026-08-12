import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * AuthCallbackPage — handles Google OAuth redirect with token in URL fragment.
 * 
 * After Google OAuth, the backend redirects to:
 *   /auth/callback#token=JWT_HERE&user=JSON_HERE
 * 
 * This page reads the fragment, stores the token, and redirects to /dashboard.
 * Using a URL fragment (hash) is safe because fragments are never sent to servers.
 */
export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const { setTokenAndUser } = useAuth();
  const [status, setStatus] = useState('Processing sign-in...');
  const [error, setError] = useState('');

  useEffect(() => {
    const hash = window.location.hash.slice(1); // remove leading '#'
    if (!hash) {
      setError('No authentication data found. Please try signing in again.');
      setTimeout(() => navigate('/login'), 3000);
      return;
    }

    try {
      const params = new URLSearchParams(hash);
      const token = params.get('token');
      const userStr = params.get('user');

      if (!token || !userStr) {
        setError('Incomplete authentication data. Please try again.');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      const user = JSON.parse(userStr);
      if (!user || !user.id) {
        setError('Invalid user data received. Please try again.');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      // Store in localStorage and update React context
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));

      // Also signal to any open popup that it can close
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.postMessage({ type: 'GOOGLE_LOGIN_SUCCESS', token, user, error: null }, '*');
          window.close();
          return;
        } catch (e) {
          // Not a popup, continue with redirect
        }
      }

      // If AuthContext exposes setTokenAndUser, use it; otherwise page reload will pick up localStorage
      if (setTokenAndUser) {
        setTokenAndUser(token, user);
      }

      setStatus('Sign-in successful! Redirecting to dashboard...');
      // Small delay so the user sees the success message
      setTimeout(() => {
        // Clear the hash from URL before navigating (security hygiene)
        window.history.replaceState(null, '', window.location.pathname);
        navigate('/dashboard', { replace: true });
      }, 800);
    } catch (err) {
      console.error('[AuthCallback] Error parsing OAuth data:', err);
      setError('Failed to process sign-in. Please try again.');
      setTimeout(() => navigate('/login'), 3000);
    }
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#0f172a',
      color: '#fff',
      fontFamily: 'sans-serif'
    }}>
      <div style={{
        textAlign: 'center',
        padding: '28px 36px',
        background: '#1e293b',
        borderRadius: '16px',
        maxWidth: '380px',
        width: '100%',
        boxShadow: '0 25px 50px rgba(0,0,0,0.5)'
      }}>
        {error ? (
          <>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>✗</div>
            <h2 style={{ color: '#ef4444', marginBottom: '8px', fontSize: '1.1rem' }}>{error}</h2>
            <p style={{ color: '#94a3b8', fontSize: '13px' }}>Returning to login...</p>
          </>
        ) : (
          <>
            <div style={{
              width: '48px',
              height: '48px',
              border: '4px solid rgba(59,130,246,0.2)',
              borderTop: '4px solid #3b82f6',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 16px'
            }} />
            <h2 style={{ color: '#10b981', marginBottom: '8px', fontSize: '1.1rem' }}>
              ✓ Google Sign-in Complete!
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '13px' }}>{status}</p>
          </>
        )}
      </div>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
