import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import API from '../services/api';
import { User, Lock, Mail, CheckCircle, AlertCircle, Save, ShieldCheck, ExternalLink, RefreshCw } from 'lucide-react';

export default function ProfilePage() {
  const { user, updateProfile } = useAuth();

  const [name, setName] = useState(user?.name || '');
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [profileMsg, setProfileMsg] = useState('');
  const [passwordMsg, setPasswordMsg] = useState('');
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get('connected') === 'true') {
      const syncGmailStatus = async () => {
        try {
          const res = await API.put('/users/profile', { gmail_connected: true });
          updateProfile(res.data.user);
          setProfileMsg('Gmail account connected successfully!');
        } catch (err) {
          console.error("Failed to sync Gmail status:", err);
        }
      };
      syncGmailStatus();
    }
  }, []);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setIsUpdatingProfile(true);
    setProfileMsg('');
    try {
      const res = await API.put('/users/profile', { name, avatar_url: avatarUrl });
      updateProfile(res.data.user);
      setProfileMsg('Profile details updated successfully!');
    } catch (err) {
      setProfileMsg(err.response?.data?.message || 'Failed to update profile.');
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setIsUpdatingPassword(true);
    setPasswordMsg('');
    try {
      const res = await API.post('/users/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      setPasswordMsg(res.data.message);
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      setPasswordMsg(err.response?.data?.message || 'Failed to change password.');
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const [isResyncing, setIsResyncing] = useState(false);
  const [resyncMsg, setResyncMsg] = useState('');

  const handleConnectGmail = async () => {
    try {
      const res = await API.get('/auth/google/url');
      if (res.data.simulated) {
        const updated = await API.put('/users/profile', { gmail_connected: !user.gmail_connected });
        updateProfile(updated.data.user);
        setProfileMsg('Gmail connection status updated!');
      } else if (res.data.auth_url) {
        const popup = window.open(
          res.data.auth_url,
          'GoogleOAuth',
          'width=600,height=700,top=100,left=300'
        );

        const handleMessage = (event) => {
          if (event.data && event.data.type === 'GMAIL_CONNECTED') {
            window.removeEventListener('message', handleMessage);
            const syncStatus = async () => {
              try {
                const res = await API.put('/users/profile', { gmail_connected: true });
                updateProfile(res.data.user);
                setProfileMsg('✓ Gmail account connected! Click "Import Real Gmail Emails" to load your actual emails.');
              } catch (err) {
                console.error(err);
              }
            };
            syncStatus();
          }
        };

        window.addEventListener('message', handleMessage);
      }
    } catch (err) {
      console.error("Gmail connect error:", err);
    }
  };

  const handleFullResync = async () => {
    setIsResyncing(true);
    setResyncMsg('');
    try {
      const res = await API.post('/emails/resync');
      setResyncMsg(`✓ ${res.data.message} (Source: ${res.data.source})`);
      setTimeout(() => setResyncMsg(''), 6000);
    } catch (err) {
      setResyncMsg('⚠ Failed to resync emails. Please try again.');
      setTimeout(() => setResyncMsg(''), 4000);
    } finally {
      setIsResyncing(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* User Header Profile Card */}
      <div className="glass-card p-6 flex flex-col sm:flex-row items-center gap-6">
        <img
          src={user?.avatar_url || "https://ui-avatars.com/api/?name=User&background=0D8ABC&color=fff"}
          alt={user?.name}
          className="w-20 h-20 rounded-2xl object-cover ring-4 ring-blue-500/20 shadow-lg"
        />
        <div className="space-y-1 text-center sm:text-left flex-1">
          <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
            <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">{user?.name}</h2>
            <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300">
              {user?.role}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">{user?.email}</p>
          <p className="text-[11px] text-slate-400">
            Account Created: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'Active'}
          </p>
        </div>

        {/* Gmail Connection Status Card */}
        <div className="p-4 rounded-2xl bg-slate-100/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 flex flex-col items-center sm:items-end gap-2 shrink-0">
          <div className="flex items-center gap-2">
            {user?.gmail_connected ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Gmail Connected</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Gmail Disconnected</span>
              </span>
            )}
          </div>
          <div className="flex flex-col gap-2">
            <button
              onClick={handleConnectGmail}
              className="px-3 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/50 hover:bg-blue-100 dark:hover:bg-blue-900/60 border border-blue-200 dark:border-blue-800 rounded-xl transition-all flex items-center gap-1.5"
            >
              <span>{user?.gmail_connected ? 'Re-auth Gmail' : 'Connect Gmail Account'}</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
            {user?.gmail_connected && (
              <button
                onClick={handleFullResync}
                disabled={isResyncing}
                className="px-3 py-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 border border-emerald-200 dark:border-emerald-800 rounded-xl transition-all flex items-center gap-1.5 disabled:opacity-50"
                title="Clear old emails and import your real Gmail messages"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isResyncing ? 'animate-spin' : ''}`} />
                <span>{isResyncing ? 'Importing...' : '📥 Import Real Gmail Emails'}</span>
              </button>
            )}
            {resyncMsg && (
              <p className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">{resyncMsg}</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Profile Details Form */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <User className="w-4 h-4 text-blue-500" />
            <span>Update Personal Profile</span>
          </h3>

          {profileMsg && (
            <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-600 dark:text-blue-400 text-xs font-medium">
              {profileMsg}
            </div>
          )}

          <form onSubmit={handleUpdateProfile} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Full Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Profile Avatar URL
              </label>
              <input
                type="url"
                value={avatarUrl}
                onChange={(e) => setAvatarUrl(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
            </div>

            <button
              type="submit"
              disabled={isUpdatingProfile}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>Save Profile Changes</span>
            </button>
          </form>
        </div>

        {/* Change Password Form */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Lock className="w-4 h-4 text-emerald-500" />
            <span>Change Security Password</span>
          </h3>

          {passwordMsg && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
              {passwordMsg}
            </div>
          )}

          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Current Password
              </label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                New Password
              </label>
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
              />
            </div>

            <button
              type="submit"
              disabled={isUpdatingPassword}
              className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl shadow-md transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Update Password</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
