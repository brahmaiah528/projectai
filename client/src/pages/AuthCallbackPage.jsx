import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * AuthCallbackPage — handles Google OAuth redirect with token in URL fragment.
 *
 * Flow:
 *  1. User clicks "Sign in with Google" → popup opens
 *  2. Google redirects to Render backend callback
 *  3. Backend does HTTP 302 redirect to: {FRONTEND_URL}/auth/callback#token=...&user=...
 *  4. This page loads in the popup (same Vercel origin as opener)
 *  5a. If popup (window.opener exists): postMessage to opener (same-origin ✅), close popup
 *      → opener's handler sets token/user state → navigate('/dashboard')
 *  5b. If direct (no popup): store token in localStorage, navigate to /dashboard directly
 */
export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const { setTokenAndUser } = useAuth();
  const [status, setStatus] = useState('Processing sign-in...');
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    const hash = window.location.hash.slice(1); // remove leading '#'

    // Check for error first
    const params = new URLSearchParams(hash);
    const errorParam = params.get('error');
    if (errorParam || !hash) {
      const msg = errorParam ? decodeURIComponent(errorParam) : 'No authentication data received.';
      setIsError(true);
      setStatus(msg);

      // If this is a popup, notify the opener of the error
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.postMessage(
            { type: 'GOOGLE_LOGIN_SUCCESS', token: null, user: null, error: msg },
            window.location.origin
          );
        } catch (e) { /* ignore */ }
        setTimeout(() => window.close(), 2500);
      } else {
        setTimeout(() => navigate('/login', { replace: true }), 2500);
      }
      return;
    }

    try {
      const token = params.get('token');
      const userStr = params.get('user');

      if (!token || !userStr) {
        setIsError(true);
        setStatus('Incomplete authentication data. Please try again.');
        setTimeout(() => navigate('/login', { replace: true }), 2500);
        return;
      }

      const user = JSON.parse(decodeURIComponent(userStr));
      if (!user || !user.id) {
        setIsError(true);
        setStatus('Invalid user data received. Please try again.');
        setTimeout(() => navigate('/login', { replace: true }), 2500);
        return;
      }

      // Clear the hash from the URL immediately (security hygiene — token gone from URL bar)
      window.history.replaceState(null, '', window.location.pathname);

      // CASE A: We're in a popup — postMessage to the opener (same-origin, always works)
      if (window.opener && !window.opener.closed) {
        try {
          window.opener.postMessage(
            { type: 'GOOGLE_LOGIN_SUCCESS', token, user, error: null },
            window.location.origin  // same-origin target — most secure
          );
          setStatus('Sign-in complete! Closing...');
          setTimeout(() => window.close(), 400);
          return;
        } catch (e) {
          console.warn('[AuthCallback] postMessage to opener failed, falling through to direct login:', e);
        }
      }

      // CASE B: No popup (direct navigation, e.g. mobile, popup blocked, or came via URL)
      // Store token directly and navigate to dashboard
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      if (setTokenAndUser) {
        setTokenAndUser(token, user);
      }
      setStatus('Sign-in successful! Redirecting to dashboard...');
      setTimeout(() => navigate('/dashboard', { replace: true }), 600);

    } catch (err) {
      console.error('[AuthCallback] Error parsing OAuth data:', err);
      setIsError(true);
      setStatus('Failed to process sign-in. Please try again.');
      setTimeout(() => navigate('/login', { replace: true }), 2500);
    }
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
      color: '#fff',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    }}>
      <div style={{
        textAlign: 'center',
        padding: '36px 40px',
        background: 'rgba(30, 41, 59, 0.95)',
        borderRadius: '20px',
        maxWidth: '400px',
        width: '90%',
        boxShadow: '0 25px 60px rgba(0,0,0,0.5)',
        border: '1px solid rgba(255,255,255,0.08)'
      }}>
        {isError ? (
          <>
            <div style={{ fontSize: '2.8rem', marginBottom: '14px', color: '#ef4444' }}>✗</div>
            <h2 style={{ color: '#ef4444', marginBottom: '8px', fontSize: '1.1rem', fontWeight: 600 }}>
              Sign-in Failed
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: 1.5 }}>{status}</p>
            <p style={{ color: '#64748b', fontSize: '12px', marginTop: '8px' }}>Redirecting back to login...</p>
          </>
        ) : (
          <>
            {/* Google logo */}
            <svg style={{ width: 48, height: 48, margin: '0 auto 16px' }} viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <div style={{
              width: '40px',
              height: '40px',
              border: '3px solid rgba(59,130,246,0.2)',
              borderTop: '3px solid #3b82f6',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              margin: '0 auto 16px'
            }} />
            <h2 style={{ color: '#10b981', marginBottom: '8px', fontSize: '1.1rem', fontWeight: 600 }}>
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
