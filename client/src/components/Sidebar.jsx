import React, { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { 
  Inbox, Star, Send, FileText, AlertOctagon, Trash2, 
  LayoutDashboard, Cpu, BarChart3, User, Shield, Tag, X, Mail, Plus,
  Clock, Bookmark
} from 'lucide-react';
import ComposeModal from './ComposeModal';

const FOLDERS = [
  { id: 'all',       label: 'All Mail',  icon: Mail,         color: 'text-indigo-500' },
  { id: 'inbox',     label: 'Inbox',     icon: Inbox,        color: 'text-blue-500' },
  { id: 'starred',   label: 'Starred',   icon: Star,         color: 'text-amber-500' },
  { id: 'important', label: 'Important', icon: Bookmark,     color: 'text-orange-500' },
  { id: 'snoozed',   label: 'Snoozed',   icon: Clock,        color: 'text-purple-500' },
  { id: 'sent',      label: 'Sent Mail', icon: Send,         color: 'text-emerald-500' },
  { id: 'drafts',    label: 'Drafts',    icon: FileText,     color: 'text-slate-500' },
  { id: 'spam',      label: 'Spam',      icon: AlertOctagon, color: 'text-rose-500' },
  { id: 'trash',     label: 'Trash',     icon: Trash2,       color: 'text-slate-400' },
];


const CATEGORIES = [
  'All', 'Immediate Reply', 'Spam', 'Important', 'Promotions', 'Banking', 
  'Jobs', 'Examinations', 'Purchases', 'Social', 'Personal', 'Updates',
  'Office', 'Customer Support', 'Bookings', 'Travel', 'Healthcare', 'Newsletters', 'Others'
];

export default function Sidebar({ 
  activeFolder, 
  setActiveFolder, 
  activeCategory, 
  setActiveCategory, 
  isOpen, 
  onClose,
  unreadCount = 0,
  isAdmin = false 
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const isInboxPage = location.pathname === '/' || location.pathname === '/inbox';
  const [isComposeOpen, setIsComposeOpen] = useState(false);

  const handleSelectFolder = (folderId) => {
    setActiveFolder(folderId);
    if (folderId === 'trash') {
      setActiveCategory('All');
    }
    if (!isInboxPage) {
      navigate('/inbox');
    }
    onClose();
  };

  const handleSelectCategory = (cat) => {
    setActiveCategory(cat);
    if (cat !== 'All' && activeFolder !== 'trash') {
      setActiveFolder('all');
    }
    if (!isInboxPage) {
      navigate('/inbox');
    }
    onClose();
  };

  const handleEmailSent = (email) => {
    setActiveFolder('sent');
    if (!isInboxPage) {
      navigate('/inbox');
    }
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          onClick={onClose} 
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40 w-64 glass-card border-r border-slate-200/80 dark:border-slate-800/80 p-4 flex flex-col justify-between transition-transform duration-200 ease-in-out shrink-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="space-y-4 overflow-y-auto pr-1">
          {/* Header Mobile Close */}
          <div className="flex items-center justify-between lg:hidden pb-2 border-b border-slate-200/80 dark:border-slate-800/80">
            <div className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-blue-600" />
              <span className="font-bold text-sm">Navigation Menu</span>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Prominent Compose Email Button */}
          <button
            onClick={() => setIsComposeOpen(true)}
            className="w-full py-2.5 px-4 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-blue-500/25 transition-all flex items-center justify-center gap-2 transform active:scale-95"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            <span>Compose Email</span>
          </button>

          {/* Main Navigation Links */}
          <div>
            <p className="px-3 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
              Main App
            </p>
            <nav className="space-y-1">
              <NavLink
                to="/dashboard"
                onClick={onClose}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-xl transition-all
                  ${isActive 
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'}
                `}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard Overview</span>
              </NavLink>

              <NavLink
                to="/inbox"
                onClick={onClose}
                className={({ isActive }) => `
                  flex items-center justify-between px-3 py-2 text-xs font-semibold rounded-xl transition-all
                  ${isActive 
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'}
                `}
              >
                <div className="flex items-center gap-3">
                  <Inbox className="w-4 h-4" />
                  <span>Email Inbox</span>
                </div>
                {unreadCount > 0 && (
                  <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-100 dark:bg-blue-900/80 text-blue-700 dark:text-blue-200">
                    {unreadCount}
                  </span>
                )}
              </NavLink>

              <NavLink
                to="/classifier-lab"
                onClick={onClose}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-xl transition-all
                  ${isActive 
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'}
                `}
              >
                <Cpu className="w-4 h-4 text-purple-500" />
                <span>AI Classifier Lab</span>
              </NavLink>

              <NavLink
                to="/analytics"
                onClick={onClose}
                className={({ isActive }) => `
                  flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-xl transition-all
                  ${isActive 
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' 
                    : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'}
                `}
              >
                <BarChart3 className="w-4 h-4 text-emerald-500" />
                <span>Analytics & Models</span>
              </NavLink>
            </nav>
          </div>

          {/* Mailbox Folders */}
          <div>
            <p className="px-3 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">
              Folders
            </p>
            <nav className="space-y-1">
              {FOLDERS.map((folder) => {
                const Icon = folder.icon;
                const isActive = activeFolder === folder.id && isInboxPage;
                return (
                  <button
                    key={folder.id}
                    onClick={() => handleSelectFolder(folder.id)}
                    className={`
                      w-full flex items-center gap-3 px-3 py-1.5 text-xs font-medium rounded-xl transition-all text-left
                      ${isActive 
                        ? 'bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold' 
                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/40'}
                    `}
                  >
                    <Icon className={`w-4 h-4 ${folder.color}`} />
                    <span>{folder.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Categories Filter */}
          <div>
            <p className="px-3 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2 flex items-center justify-between">
              <span>AI Categories</span>
              <Tag className="w-3 h-3" />
            </p>
            <div className="flex flex-wrap gap-1 px-1 max-h-52 overflow-y-auto pr-1">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  onClick={() => handleSelectCategory(cat)}
                  className={`
                    px-2.5 py-1 text-[11px] font-medium rounded-lg border transition-all
                    ${activeCategory === cat && isInboxPage
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800 hover:bg-slate-200 dark:hover:bg-slate-800'}
                  `}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom Profile & Admin Nav */}
        <div className="pt-4 border-t border-slate-200/80 dark:border-slate-800/80 space-y-1 shrink-0">
          <NavLink
            to="/profile"
            onClick={onClose}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-xl transition-all
              ${isActive 
                ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' 
                : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'}
            `}
          >
            <User className="w-4 h-4" />
            <span>Account Profile</span>
          </NavLink>

          {isAdmin && (
            <NavLink
              to="/admin"
              onClick={onClose}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2 text-xs font-semibold rounded-xl transition-all
                ${isActive 
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20' 
                  : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60'}
              `}
            >
              <Shield className="w-4 h-4 text-indigo-500" />
              <span>Admin Management</span>
            </NavLink>
          )}
        </div>
      </aside>

      <ComposeModal 
        isOpen={isComposeOpen} 
        onClose={() => setIsComposeOpen(false)} 
        onEmailSent={handleEmailSent}
      />
    </>
  );
}
