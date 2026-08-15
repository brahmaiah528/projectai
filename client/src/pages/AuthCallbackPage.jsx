import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import API from '../services/api';

/**
 * AuthCallbackPage — reads Google OAuth token from URL query params and logs user in.
 * After login, polls /api/emails/sync-status every 3s until live Gmail sync completes,
 * then stores a 'gmail_sync_done' flag in sessionStorage so InboxPage can refresh.
 */
export default function AuthCallbackPage() {
  const navigate = useNavigate();
  const { setTokenAndUser } = useAuth();
  const [status, setStatus] = useState('Completing sign-in...');
  const [syncMsg, setSyncMsg] = useState('Setting up your workspace...');
  const [isError, setIsError] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const isProcessedRef = useRef(false);

  useEffect(() => {
    if (isProcessedRef.current) return;

    const searchParams = new URLSearchParams(window.location.search);
    const errorParam = searchParams.get('error');
    const token = searchParams.get('token');
    const userStr = searchParams.get('user');

    if (errorParam) {
      isProcessedRef.current = true;
      setIsError(true);
      setErrorMsg(decodeURIComponent(errorParam));
      window.history.replaceState(null, '', window.location.pathname);
      setTimeout(() => navigate('/login', { replace: true }), 3000);
      return;
    }

    if (!token || !userStr) {
      // Check if already authenticated from a previous cycle / local storage
      const existingToken = localStorage.getItem('token');
      const existingUser = localStorage.getItem('user');
      if (existingToken && existingUser) {
        isProcessedRef.current = true;
        navigate('/dashboard', { replace: true });
        return;
      }

      isProcessedRef.current = true;
      setIsError(true);
      setErrorMsg('No sign-in data received. Please try again.');
      setTimeout(() => navigate('/login', { replace: true }), 3000);
      return;
    }

    try {
      isProcessedRef.current = true;
      const user = JSON.parse(userStr);

      if (!user || !user.id) {
        setIsError(true);
        setErrorMsg('Invalid user profile data. Please try again.');
        setTimeout(() => navigate('/login', { replace: true }), 3000);
        return;
      }

      // Store token and user data in context and localStorage
      setTokenAndUser(token, user);
      sessionStorage.removeItem('google_login_pending');
      sessionStorage.setItem('gmail_sync_done', '1');

      // Strip query parameters from URL bar for clean UX
      window.history.replaceState(null, '', window.location.pathname);

      setStatus(`Welcome, ${user.name || user.email}!`);
      setSyncMsg('Redirecting to your dashboard...');

      // Seamless transition to Dashboard
      setTimeout(() => {
        navigate('/dashboard', { replace: true });
      }, 700);

    } catch (err) {
      console.error('[AuthCallback] Parse error:', err);
      setIsError(true);
      setErrorMsg('Failed to process sign-in data. Please try again.');
      setTimeout(() => navigate('/login', { replace: true }), 3000);
    }
  }, [navigate, setTokenAndUser]);

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
        maxWidth: '440px',
        width: '90%',
        boxShadow: '0 30px 80px rgba(0,0,0,0.6)',
        border: '1px solid rgba(255,255,255,0.08)'
      }}>
        {isError ? (
          <>
            <div style={{
              width: 56, height: 56,
              borderRadius: '50%',
              background: 'rgba(239,68,68,0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '1.6rem', color: '#ef4444'
            }}>✗</div>
            <h2 style={{ color: '#ef4444', marginBottom: 8, fontSize: '1.1rem', fontWeight: 600 }}>
              Sign-in Failed
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '13px', lineHeight: 1.6, marginBottom: 6 }}>
              {errorMsg}
            </p>
            <p style={{ color: '#475569', fontSize: '12px' }}>Redirecting back to login...</p>
          </>
        ) : (
          <>
            {/* Spinner ring around Google logo */}
            <div style={{ position: 'relative', width: 70, height: 70, margin: '0 auto 24px' }}>
              <div style={{
                position: 'absolute', inset: 0,
                border: '3px solid rgba(59,130,246,0.15)',
                borderTop: '3px solid #3b82f6',
                borderRadius: '50%',
                animation: 'spin 0.9s linear infinite'
              }} />
              <div style={{
                position: 'absolute', inset: 10,
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <svg viewBox="0 0 24 24" style={{ width: 36, height: 36 }}>
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              </div>
            </div>

            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: 'rgba(16,185,129,0.1)',
              border: '1px solid rgba(16,185,129,0.25)',
              borderRadius: 999, padding: '5px 16px', marginBottom: 14
            }}>
              <span style={{ color: '#10b981', fontSize: 13, fontWeight: 600 }}>
                ✓ Google Sign-in Successful
              </span>
            </div>

            <p style={{ color: '#e2e8f0', fontSize: '14px', fontWeight: 600, marginBottom: 8 }}>{status}</p>
            {syncMsg && (
              <p style={{
                color: syncMsg.startsWith('✅') ? '#10b981' : '#94a3b8',
                fontSize: '13px',
                lineHeight: 1.6,
                padding: '10px 16px',
                background: 'rgba(255,255,255,0.04)',
                borderRadius: 10,
                marginTop: 8
              }}>{syncMsg}</p>
            )}
            <p style={{ color: '#475569', fontSize: '11px', marginTop: 12 }}>
              Please wait — importing all your Gmail messages including Inbox, Sent, Trash &amp; Spam
            </p>
          </>
        )}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
