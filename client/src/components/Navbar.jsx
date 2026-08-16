import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { 
  Search, RefreshCw, Sun, Moon, LogOut, User, 
  Shield, CheckCircle, AlertCircle, Menu 
} from 'lucide-react';
import API from '../services/api';

export default function Navbar({ searchQuery, setSearchQuery, onSyncComplete, toggleSidebar }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState('');
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncMsg('');
    try {
      const res = await API.post('/emails/delta-sync');
      const changes = res.data.changes || 0;
      setSyncMsg(changes > 0 ? `✓ ${changes} Gmail change(s) synced!` : `✓ In sync with Gmail`);
      if (onSyncComplete) onSyncComplete(changes);
      // Dispatch custom event so any active page refreshes immediately
      window.dispatchEvent(new CustomEvent('gmail-synced'));
      setTimeout(() => setSyncMsg(''), 4000);
    } catch (err) {
      try {
        const fullRes = await API.post('/emails/sync');
        setSyncMsg('✓ Full Gmail sync triggered');
        window.dispatchEvent(new CustomEvent('gmail-synced'));
        setTimeout(() => setSyncMsg(''), 4000);
      } catch (e) {
        setSyncMsg('⚠ Sync failed');
        setTimeout(() => setSyncMsg(''), 3000);
      }
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <header className="sticky top-0 z-30 h-16 glass-header px-4 flex items-center justify-between gap-4">
      {/* Left: Mobile Menu Toggle & Brand Title */}
      <div className="flex items-center gap-3">
        <button 
          onClick={toggleSidebar}
          className="p-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
            <span className="text-lg">AI</span>
          </div>
          <div className="hidden sm:block">
            <h1 className="text-sm font-bold bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent">
              EmailClassifier AI
            </h1>
            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
              Automated Content Categorization
            </p>
          </div>
        </div>
      </div>

      {/* Middle: Search Bar */}
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery || ''}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search emails by sender, subject, body, or category..."
            className="w-full pl-10 pr-4 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-slate-800 dark:text-slate-200 placeholder-slate-400"
          />
        </div>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-2">
        {/* Sync Button */}
        <button
          onClick={handleSync}
          disabled={isSyncing}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/50 border border-blue-200 dark:border-blue-800/60 rounded-xl transition-all disabled:opacity-50"
          title="Sync latest emails from Gmail API"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
          <span className="hidden md:inline">{isSyncing ? 'Syncing...' : 'Sync Emails'}</span>
        </button>

        {/* Sync Toast */}
        {syncMsg && (
          <span className="hidden md:inline text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 rounded-lg px-2.5 py-1 animate-in fade-in duration-200">
            {syncMsg}
          </span>
        )}

        {/* Gmail Status Badge - dynamic */}
        <div className={`hidden xl:flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium rounded-full border ${
          user?.gmail_connected 
            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
            : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
        }`}>
          {user?.gmail_connected ? (
            <><CheckCircle className="w-3 h-3" /><span>Gmail Connected</span></>
          ) : (
            <><AlertCircle className="w-3 h-3" /><span>Gmail Not Linked</span></>
          )}
        </div>

        {/* Dark/Light Mode Switcher */}
        <button
          onClick={toggleTheme}
          className="p-2 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
        </button>

        {/* Profile Avatar & Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowUserDropdown(!showUserDropdown)}
            className="flex items-center gap-2 p-1 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus:outline-none"
          >
            <img
              src={user?.avatar_url || "https://ui-avatars.com/api/?name=User&background=0D8ABC&color=fff"}
              alt={user?.name}
              className="w-8 h-8 rounded-lg object-cover ring-2 ring-blue-500/30"
            />
          </button>

          {showUserDropdown && (
            <div className="absolute right-0 mt-2 w-56 glass-card p-2 shadow-xl border z-50 animate-in fade-in zoom-in-95 duration-100">
              <div className="px-3 py-2 border-b border-slate-200/80 dark:border-slate-800/80 mb-1">
                <p className="text-xs font-bold text-slate-900 dark:text-slate-100">{user?.name}</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{user?.email}</p>
                <span className="inline-block mt-1 px-1.5 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300">
                  {user?.role}
                </span>
              </div>
              
              <Link
                to="/profile"
                onClick={() => setShowUserDropdown(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
              >
                <User className="w-4 h-4" />
                <span>My Profile</span>
              </Link>

              {user?.role === 'admin' && (
                <Link
                  to="/admin"
                  onClick={() => setShowUserDropdown(false)}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
                >
                  <Shield className="w-4 h-4 text-indigo-500" />
                  <span>Admin Panel</span>
                </Link>
              )}

              <button
                onClick={() => {
                  setShowUserDropdown(false);
                  logout();
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition-colors mt-1 cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
