import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * AuthCallbackPage — reads Google OAuth token from URL fragment and logs user in.
 *
 * The backend redirects here after OAuth:
 *   /auth/callback#token=JWT&user={...}   ← success
 *   /auth/callback#error=message          ← failure
 *
 * This is a full-page load on the same Vercel domain — no popups, no postMessage.
 * Simply reads the fragment, stores the token, and navigates to /dashboard.
 */
export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const { setTokenAndUser } = useAuth();
  const [status, setStatus] = useState('Completing sign-in...');
  const [isError, setIsError] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const hash = window.location.hash.slice(1); // remove '#'

    if (!hash) {
      setIsError(true);
      setErrorMsg('No authentication data found.');
      setTimeout(() => navigate('/login', { replace: true }), 3000);
      return;
    }

    const params = new URLSearchParams(hash);
    const errorParam = params.get('error');

    if (errorParam) {
      const msg = decodeURIComponent(errorParam);
      setIsError(true);
      setErrorMsg(msg);
      setTimeout(() => navigate('/login', { replace: true }), 3000);
      return;
    }

    try {
      const token = params.get('token');
      const userStr = params.get('user');

      if (!token || !userStr) {
        setIsError(true);
        setErrorMsg('Incomplete sign-in data. Please try again.');
        setTimeout(() => navigate('/login', { replace: true }), 3000);
        return;
      }

      const user = JSON.parse(userStr);
      if (!user || !user.id) {
        setIsError(true);
        setErrorMsg('Invalid user data. Please try again.');
        setTimeout(() => navigate('/login', { replace: true }), 3000);
        return;
      }

      // Clear the fragment from the URL bar immediately (security — remove token from URL)
      window.history.replaceState(null, '', window.location.pathname);

      // Store in localStorage AND update React context
      setTokenAndUser(token, user);
      sessionStorage.removeItem('google_login_pending');

      setStatus(`Welcome, ${user.name || user.email}! Redirecting to dashboard...`);

      // Short delay so user sees the success message, then navigate
      setTimeout(() => {
        navigate('/dashboard', { replace: true });
      }, 800);

    } catch (err) {
      console.error('[AuthCallback] Parse error:', err);
      setIsError(true);
      setErrorMsg('Failed to process sign-in. Please try again.');
      setTimeout(() => navigate('/login', { replace: true }), 3000);
    }
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    }}>
      <div style={{
        textAlign: 'center',
        padding: '40px 48px',
        background: 'rgba(30, 41, 59, 0.98)',
        borderRadius: '20px',
        maxWidth: '420px',
        width: '90%',
        boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
        border: '1px solid rgba(255,255,255,0.08)'
      }}>
        {isError ? (
          <>
            <div style={{
              width: 56, height: 56,
              borderRadius: '50%',
              background: 'rgba(239,68,68,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '1.8rem'
            }}>✗</div>
            <h2 style={{ color: '#ef4444', marginBottom: 8, fontSize: '1.15rem', fontWeight: 600 }}>
              Sign-in Failed
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: 1.6, marginBottom: 6 }}>
              {errorMsg}
            </p>
            <p style={{ color: '#475569', fontSize: '12px' }}>
              Redirecting back to login...
            </p>
          </>
        ) : (
          <>
            {/* Animated Google logo + spinner */}
            <div style={{ position: 'relative', width: 64, height: 64, margin: '0 auto 20px' }}>
              <div style={{
                position: 'absolute', inset: 0,
                border: '3px solid rgba(59,130,246,0.15)',
                borderTop: '3px solid #3b82f6',
                borderRadius: '50%',
                animation: 'spin 0.9s linear infinite'
              }} />
              <div style={{
                position: 'absolute', inset: 8,
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <svg viewBox="0 0 24 24" style={{ width: 32, height: 32 }}>
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              </div>
            </div>

            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: 'rgba(16,185,129,0.12)',
              border: '1px solid rgba(16,185,129,0.3)',
              borderRadius: 999,
              padding: '4px 14px',
              marginBottom: 16
            }}>
              <span style={{ color: '#10b981', fontSize: 13, fontWeight: 600 }}>
                ✓ Google Sign-in Complete
              </span>
            </div>

            <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: 1.6 }}>
              {status}
            </p>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
