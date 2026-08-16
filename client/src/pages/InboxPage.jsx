import React, { useState, useEffect, useRef, useMemo } from 'react';
import API from '../services/api';
import CategoryBadge, { PriorityActionBadge } from '../components/CategoryBadge';
import { 
  Star, Mail, MailOpen, Trash2, CheckSquare, Square, 
  ArrowUpDown, Filter, Inbox, AlertCircle,
  ArrowLeft, Calendar, User, Cpu, ShieldCheck, RotateCcw,
  Clock, Bookmark, BookmarkCheck, Bell, BellOff, X, RefreshCw,
  ChevronLeft, ChevronRight
} from 'lucide-react';

/** Strip HTML tags and return clean readable text */
function stripHtml(html) {
  if (!html) return '';
  try {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.textContent || div.innerText || '';
  } catch (_) {
    return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  }
}

/** Renders HTML email body visually inside a sandboxed iframe */
function EmailBodyRenderer({ rawBody }) {
  if (!rawBody || !rawBody.trim()) {
    return (
      <div className="p-6 text-slate-400 italic text-sm bg-slate-50 dark:bg-slate-900/40 rounded-xl m-4 border border-dashed border-slate-200 dark:border-slate-800 flex items-center justify-center gap-2">
        <AlertCircle className="w-4 h-4 text-slate-400" />
        <span>No detailed HTML body content in this message.</span>
      </div>
    );
  }

  let html = rawBody;
  if (html.includes('&lt;') || html.includes('&gt;')) {
    try {
      const ta = document.createElement('textarea');
      ta.innerHTML = html;
      html = ta.value;
      if (html.includes('&lt;')) { ta.innerHTML = html; html = ta.value; }
    } catch (_) {}
  }

  const isHtml = /\<[a-z]/i.test(html);
  if (!isHtml) {
    return (
      <div className="whitespace-pre-wrap text-slate-800 dark:text-slate-200 leading-relaxed text-sm p-6">
        {rawBody}
      </div>
    );
  }

  const fullHtmlDoc = /\<html/i.test(html) ? html : `<!DOCTYPE html><html><head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <style>
      body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#1e293b;margin:0;padding:16px;font-size:14px;line-height:1.6;background:#fff;}
      img{max-width:100%!important;height:auto!important;display:block;margin:8px 0;}
      table{max-width:100%!important;}
      a{color:#2563eb;}
    </style>
  </head><body>${html}</body></html>`;

  return (
    <iframe
      srcDoc={fullHtmlDoc}
      title="Email Preview"
      className="w-full border-0 bg-white block min-h-[420px]"
      style={{ minHeight: '420px', width: '100%' }}
      sandbox="allow-popups"
    />
  );
}

/** Snooze picker dropdown */
function SnoozePicker({ email, onSnooze, onClose }) {
  const presets = [
    { key: '1h',        label: 'In 1 hour',        icon: '⏰' },
    { key: '3h',        label: 'In 3 hours',       icon: '⏱️' },
    { key: 'tomorrow',  label: 'Tomorrow morning',  icon: '🌅' },
    { key: 'next_week', label: 'Next week',         icon: '📅' },
  ];

  return (
    <div className="absolute right-0 top-10 z-50 w-52 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
      <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Snooze until...</span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      {presets.map(p => (
        <button
          key={p.key}
          onClick={() => { onSnooze(email.id, p.key); onClose(); }}
          className="w-full text-left px-3 py-2.5 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 flex items-center gap-2.5 text-slate-700 dark:text-slate-300 transition-colors"
        >
          <span className="text-base">{p.icon}</span>
          <span>{p.label}</span>
        </button>
      ))}
      {email.is_snoozed && (
        <button
          onClick={() => { onSnooze(email.id, 'unsnooze'); onClose(); }}
          className="w-full text-left px-3 py-2.5 text-xs font-semibold hover:bg-blue-50 dark:hover:bg-blue-950 flex items-center gap-2.5 text-blue-600 dark:text-blue-400 border-t border-slate-100 dark:border-slate-800 transition-colors"
        >
          <BellOff className="w-4 h-4" />
          <span>Remove snooze</span>
        </button>
      )}
    </div>
  );
}

const ALL_CATEGORIES = [
  'All', 'Immediate Reply', 'Banking', 'Jobs', 'Examinations', 'Purchases', 
  'Promotions', 'Social', 'Personal', 'Updates', 'Office', 'Customer Support', 
  'Bookings', 'Travel', 'Healthcare', 'Newsletters', 'Spam', 'Important', 'Others'
];

export default function InboxPage({ activeFolder, setActiveFolder, activeCategory, setActiveCategory, searchQuery }) {
  const [emails, setEmails] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [activeEmail, setActiveEmail] = useState(null);
  const [sortBy, setSortBy] = useState('date_desc');
  const [isLoading, setIsLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 30;
  const [replyText, setReplyText] = useState('');
  const [isSendingReply, setIsSendingReply] = useState(false);
  const [replySuccess, setReplySuccess] = useState(false);
  const [snoozePickerFor, setSnoozePickerFor] = useState(null); // email id
  const [isSyncing, setIsSyncing] = useState(false);
  const categoryCacheRef = useRef({});
  // Track which category the current `emails` array belongs to
  // so we don't filter emails from a different category before the new fetch completes
  const [loadedCategory, setLoadedCategory] = useState('All');
  const [loadedFolder, setLoadedFolder] = useState('inbox');

  // Only show filtered emails when the loaded data actually matches the active selection
  // This prevents the "No messages found" flash when switching categories
  const displayedEmails = useMemo(() => {
    if (!emails || emails.length === 0) return [];
    // If the emails we have belong to a different category/folder, don't filter — show loading
    const categoryMatches = !activeCategory || activeCategory === 'All' || loadedCategory === activeCategory;
    const folderMatches = loadedFolder === activeFolder;
    if (!categoryMatches || !folderMatches) return null; // null = still loading
    if (!activeCategory || activeCategory === 'All') return emails;
    return emails.filter(e => (e.category || '').toLowerCase() === activeCategory.toLowerCase());
  }, [emails, activeCategory, activeFolder, loadedCategory, loadedFolder]);

  const handleManualSync = async () => {
    setIsSyncing(true);
    try {
      const res = await API.post('/emails/delta-sync');
      // Always refetch after manual sync (user explicitly requested it)
      await fetchEmails(true);
    } catch (err) {
      // Fallback to full sync if delta-sync fails
      try {
        await API.post('/emails/sync');
        await fetchEmails(true);
      } catch (_) {
        console.error("Sync failed:", err);
      }
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSendInboxReply = async () => {
    if (!replyText.trim() || !activeEmail) return;
    setIsSendingReply(true);
    try {
      await API.post('/emails/send', {
        recipient: activeEmail.sender_email || activeEmail.sender,
        subject: `Re: ${activeEmail.subject}`,
        body: replyText
      });
      setReplySuccess(true);
      setReplyText('');
      setTimeout(() => setReplySuccess(false), 4000);
    } catch (err) {
      console.error("Failed to send reply:", err);
    } finally {
      setIsSendingReply(false);
    }
  };

  useEffect(() => {
    setCurrentPage(1);
    fetchEmails(emails.length > 0).then?.(() => {});

    // After initial load, pre-fetch ALL categories silently in the background
    // so every category switch is instant (served from cache, 0ms)
    const prefetchTimer = setTimeout(() => {
      prefetchAllCategories();
    }, 1500); // 1.5s delay — let the main fetch settle first

    const doDeltaSync = () => {
      API.post('/emails/delta-sync')
        .then((res) => {
          if (res.data?.changes > 0) {
            // Instant refetch if changes were detected in Gmail
            fetchEmails(true);
          }
        })
        .catch(() => {});
    };

    // Auto delta-sync with Gmail API every 30 seconds for background mirroring
    const interval = setInterval(doDeltaSync, 30000);

    // Instant delta-sync when user returns / focuses the app tab from Gmail
    const onFocus = () => doDeltaSync();
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        doDeltaSync();
      }
    };
    const onGmailSynced = () => fetchEmails(true);

    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('gmail-synced', onGmailSynced);

    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('gmail-synced', onGmailSynced);
      clearTimeout(prefetchTimer);
    };
  }, [activeFolder, activeCategory, searchQuery, sortBy]);


  const fetchEmails = async (silent = false) => {
    const cacheKey = `${activeFolder}_${activeCategory}_${searchQuery || ''}_${sortBy}`;
    
    // 1. Instant 0ms render from memory cache if available
    if (categoryCacheRef.current[cacheKey]) {
      setEmails(categoryCacheRef.current[cacheKey]);
      setLoadedCategory(activeCategory || 'All');
      setLoadedFolder(activeFolder);
      setIsLoading(false);
      return; // Cache hit — done, no need to fetch
    } else if (!silent) {
      // No cache — clear emails immediately so we show spinner not stale/wrong data
      setEmails([]);
      setIsLoading(true);
    }

    try {
      const res = await API.get('/emails', {
        params: {
          folder: activeFolder,
          category: activeCategory,
          search: searchQuery,
          sort: sortBy
        }
      });
      const fetched = res.data?.emails || [];
      categoryCacheRef.current[cacheKey] = fetched;
      setEmails(fetched);
      setLoadedCategory(activeCategory || 'All');
      setLoadedFolder(activeFolder);
    } catch (err) {
      console.error("Failed to fetch emails:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Pre-fetch ALL categories in the background after initial load
  // so every category switch is instant (0ms from cache)
  const prefetchAllCategories = async () => {
    const categories = [
      'Immediate Reply', 'Banking', 'Jobs', 'Examinations', 'Purchases',
      'Promotions', 'Social', 'Personal', 'Updates', 'Office',
      'Customer Support', 'Bookings', 'Travel', 'Healthcare',
      'Newsletters', 'Spam', 'Important', 'Others'
    ];
    for (const cat of categories) {
      const cacheKey = `${activeFolder}_${cat}__${sortBy}`;
      if (categoryCacheRef.current[cacheKey]) continue; // already cached
      try {
        const res = await API.get('/emails', {
          params: { folder: activeFolder, category: cat, sort: sortBy }
        });
        const fetched = res.data?.emails || [];
        categoryCacheRef.current[cacheKey] = fetched;
      } catch (_) {}
      // Small delay between each so we don't hammer the server
      await new Promise(r => setTimeout(r, 80));
    }
  };

  const handleOpenEmail = (email) => {
    if (!email) return;
    // 1. Instantly open reader in 0ms!
    const updated = { ...email, is_read: true };
    setActiveEmail(updated);
    setEmails(prev => prev.map(e => e.id === email.id ? updated : e));

    // 2. Fetch full detail & mark read on backend in background without blocking UI
    API.get(`/emails/${email.id}`)
      .then(res => {
        if (res.data?.email) {
          const fullEmail = { ...res.data.email, is_read: true };
          setActiveEmail(prev => (prev && prev.id === email.id ? fullEmail : prev));
        }
      })
      .catch(err => console.warn("Background detail fetch error:", err));
  };

  const handleToggleStar = async (emailId, currentStarred) => {
    try {
      await API.patch(`/emails/${emailId}`, { is_starred: !currentStarred });
      setEmails(prev => prev.map(e => e.id === emailId ? { ...e, is_starred: !currentStarred } : e));
      if (activeEmail && activeEmail.id === emailId) {
        setActiveEmail(prev => ({ ...prev, is_starred: !currentStarred }));
      }
    } catch (err) {
      console.error("Failed to star email:", err);
    }
  };

  const handleToggleImportant = async (emailId, currentImportant) => {
    try {
      await API.patch(`/emails/${emailId}`, { is_important: !currentImportant });
      setEmails(prev => prev.map(e => e.id === emailId ? { ...e, is_important: !currentImportant } : e));
      if (activeEmail && activeEmail.id === emailId) {
        setActiveEmail(prev => ({ ...prev, is_important: !currentImportant }));
      }
    } catch (err) {
      console.error("Failed to toggle important:", err);
    }
  };

  const handleToggleRead = async (emailId, currentRead) => {
    try {
      await API.patch(`/emails/${emailId}`, { is_read: !currentRead });
      setEmails(prev => prev.map(e => e.id === emailId ? { ...e, is_read: !currentRead } : e));
      if (activeEmail && activeEmail.id === emailId) {
        setActiveEmail(prev => ({ ...prev, is_read: !currentRead }));
      }
    } catch (err) {
      console.error("Failed to update read status:", err);
    }
  };

  const handleSnooze = async (emailId, preset) => {
    try {
      const res = await API.patch(`/emails/${emailId}/snooze`, { preset });
      // Remove from current list if snoozed (not in snoozed folder) or restore if unsnoozed
      if (preset === 'unsnooze') {
        setEmails(prev => prev.map(e => e.id === emailId ? { ...e, is_snoozed: false, snoozed_until: null } : e));
      } else {
        if (activeFolder !== 'snoozed') {
          setEmails(prev => prev.filter(e => e.id !== emailId));
        }
      }
      if (activeEmail && activeEmail.id === emailId) setActiveEmail(null);
    } catch (err) {
      console.error("Failed to snooze email:", err);
    }
    setSnoozePickerFor(null);
  };

  const handleDelete = async (emailId) => {
    try {
      await API.delete(`/emails/${emailId}`);
      setEmails(prev => prev.filter(e => e.id !== emailId));
      setActiveEmail(null);
    } catch (err) {
      console.error("Failed to delete email:", err);
    }
  };

  const handleRestore = async (emailId) => {
    try {
      await API.patch(`/emails/${emailId}`, { folder: 'inbox' });
      setEmails(prev => prev.filter(e => e.id !== emailId));
      setActiveEmail(null);
    } catch (err) {
      console.error("Failed to restore email:", err);
    }
  };

  const handleBulkAction = async (action) => {
    if (selectedIds.length === 0) return;
    try {
      await API.post('/emails/bulk', { ids: selectedIds, action });
      setSelectedIds([]);
      fetchEmails();
    } catch (err) {
      console.error("Bulk action failed:", err);
    }
  };

  const handleSelectAll = () => {
    if (selectedIds.length === emails.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(emails.map(e => e.id));
    }
  };

  const toggleSelectOne = (id, e) => {
    e.stopPropagation();
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  // Format snooze time label
  const formatSnoozeLabel = (isoStr) => {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    const now = new Date();
    const diff = d - now;
    if (diff < 3600000) return `Snoozed for ${Math.round(diff/60000)}m`;
    if (diff < 86400000) return `Snoozed until ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    return `Snoozed until ${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}`;
  };

  // Email detail view
  if (activeEmail) {
    return (
      <div className="space-y-4 max-w-5xl mx-auto animate-in fade-in duration-150">
        {/* Back Button & Action Toolbar */}
        <div className="glass-card p-4 flex items-center justify-between gap-4 flex-wrap">
          <button
            onClick={() => setActiveEmail(null)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-all border border-slate-200 dark:border-slate-800"
          >
            <ArrowLeft className="w-4 h-4 text-blue-500" />
            <span>Back to Email List</span>
          </button>

          <div className="flex items-center gap-2 flex-wrap">
            <CategoryBadge category={activeEmail.category} size="md" />

            {/* Star */}
            <button
              onClick={() => handleToggleStar(activeEmail.id, activeEmail.is_starred)}
              className={`p-2 rounded-xl border transition-colors ${
                activeEmail.is_starred 
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-500' 
                  : 'border-slate-200 dark:border-slate-800 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
              title={activeEmail.is_starred ? "Starred" : "Star message"}
            >
              <Star className={`w-4 h-4 ${activeEmail.is_starred ? 'fill-amber-500' : ''}`} />
            </button>

            {/* Important */}
            <button
              onClick={() => handleToggleImportant(activeEmail.id, activeEmail.is_important)}
              className={`p-2 rounded-xl border transition-colors ${
                activeEmail.is_important
                  ? 'bg-orange-500/10 border-orange-500/30 text-orange-500'
                  : 'border-slate-200 dark:border-slate-800 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
              title={activeEmail.is_important ? "Marked Important" : "Mark as Important"}
            >
              {activeEmail.is_important
                ? <BookmarkCheck className="w-4 h-4 fill-orange-500" />
                : <Bookmark className="w-4 h-4" />
              }
            </button>

            {/* Snooze */}
            <div className="relative">
              <button
                onClick={() => setSnoozePickerFor(snoozePickerFor === activeEmail.id ? null : activeEmail.id)}
                className={`p-2 rounded-xl border transition-colors ${
                  activeEmail.is_snoozed
                    ? 'bg-purple-500/10 border-purple-500/30 text-purple-500'
                    : 'border-slate-200 dark:border-slate-800 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
                title={activeEmail.is_snoozed ? "Snoozed" : "Snooze email"}
              >
                <Clock className="w-4 h-4" />
              </button>
              {snoozePickerFor === activeEmail.id && (
                <SnoozePicker
                  email={activeEmail}
                  onSnooze={handleSnooze}
                  onClose={() => setSnoozePickerFor(null)}
                />
              )}
            </div>

            {/* Read toggle */}
            <button
              onClick={() => handleToggleRead(activeEmail.id, activeEmail.is_read)}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title={activeEmail.is_read ? "Mark as unread" : "Mark as read"}
            >
              {activeEmail.is_read ? <Mail className="w-4 h-4" /> : <MailOpen className="w-4 h-4" />}
            </button>

            {activeEmail.folder === 'trash' || activeFolder === 'trash' ? (
              <>
                <button
                  onClick={() => handleRestore(activeEmail.id)}
                  className="px-3 py-1.5 rounded-xl border border-emerald-300 dark:border-emerald-800 text-xs font-bold text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950 flex items-center gap-1.5 transition-colors"
                  title="Restore to Inbox"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Restore to Inbox</span>
                </button>
                <button
                  onClick={() => handleDelete(activeEmail.id)}
                  className="px-3 py-1.5 rounded-xl border border-rose-300 dark:border-rose-900/50 text-xs font-bold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 flex items-center gap-1.5 transition-colors"
                  title="Permanently Delete Email"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete Permanently</span>
                </button>
              </>
            ) : (
              <button
                onClick={() => handleDelete(activeEmail.id)}
                className="p-2 rounded-xl border border-rose-200 dark:border-rose-900/50 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
                title="Move to Trash"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Main Email Card */}
        <div className="glass-card overflow-hidden shadow-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
          {/* Header Info */}
          <div className="p-6 space-y-4 border-b border-slate-200 dark:border-slate-800">
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 leading-snug">
              {activeEmail.subject}
            </h1>

            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-bold flex items-center justify-center text-base shadow-md">
                  {activeEmail.sender ? activeEmail.sender[0].toUpperCase() : 'U'}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    <span>{activeEmail.sender}</span>
                    <span className="text-xs font-normal text-slate-400">&lt;{activeEmail.sender_email}&gt;</span>
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    To: <span className="font-medium">{activeEmail.recipient}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Status badges */}
                {activeEmail.is_important && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/30 text-orange-600 text-[10px] font-bold">
                    <Bookmark className="w-3 h-3" /> Important
                  </span>
                )}
                {activeEmail.is_snoozed && (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-600 text-[10px] font-bold">
                    <Clock className="w-3 h-3" /> {formatSnoozeLabel(activeEmail.snoozed_until)}
                  </span>
                )}
                <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                  <Calendar className="w-4 h-4" />
                  <span>{activeEmail.date ? new Date(activeEmail.date).toLocaleString() : 'Just now'}</span>
                </div>
              </div>
            </div>

            {/* AI Classification Banner */}
            <div className="p-3.5 rounded-2xl bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200/80 dark:border-blue-800/60 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <Cpu className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                <div>
                  <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                    AI Categorized as <span className="text-blue-600 dark:text-blue-400 font-bold">{activeEmail.category}</span>
                  </p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Machine Learning Model: Multinomial Naive Bayes + TF-IDF Vectorizer
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-28 bg-slate-200 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div 
                    className="bg-blue-600 h-full rounded-full transition-all duration-300"
                    style={{ width: `${activeEmail.confidence || 90}%` }}
                  />
                </div>
                <span className="text-xs font-bold text-blue-600 dark:text-blue-400">
                  {activeEmail.confidence || 90}%
                </span>
              </div>
            </div>
          </div>

          {/* Email Body Content — rendered visually via iframe */}
          <div className="overflow-hidden">
            <EmailBodyRenderer rawBody={activeEmail.body || activeEmail.snippet || ''} />
          </div>

          {/* Quick Reply Box */}
          <div className="p-5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 rounded-b-2xl space-y-3">
            <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
              <RotateCcw className="w-4 h-4 text-blue-500" />
              <span>Send Immediate Reply to {activeEmail.sender}</span>
            </h4>

            {replySuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-semibold flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                <span>Reply successfully sent to {activeEmail.sender_email || activeEmail.sender}!</span>
              </div>
            )}

            <textarea
              rows={3}
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder={`Write your immediate response to ${activeEmail.sender}...`}
              className="w-full p-3 text-xs bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 dark:text-slate-100"
            />
            <div className="flex justify-end">
              <button
                onClick={handleSendInboxReply}
                disabled={isSendingReply || !replyText.trim()}
                className="px-4 py-2 text-xs font-bold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl shadow-md transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {isSendingReply ? (
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <><RotateCcw className="w-3.5 h-3.5" /><span>Send Immediate Reply</span></>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Folder-specific banner configs
  const folderBanners = {
    trash: {
      show: true, color: 'rose',
      icon: <Trash2 className="w-5 h-5" />,
      title: 'Trash Folder',
      desc: 'Showing deleted messages. Restore to Inbox or permanently delete them.'
    },
    snoozed: {
      show: true, color: 'purple',
      icon: <Clock className="w-5 h-5" />,
      title: 'Snoozed Emails',
      desc: 'Emails hidden until their scheduled snooze time. They will reappear in your Inbox automatically.'
    },
    important: {
      show: true, color: 'orange',
      icon: <Bookmark className="w-5 h-5" />,
      title: 'Important Emails',
      desc: 'Emails marked as Important — synced bidirectionally with your Gmail Important label.'
    },
  };

  const banner = folderBanners[activeFolder];

  return (
    <div className="space-y-4">
      {/* Folder Banner */}
      {banner?.show && (
        <div className={`p-4 rounded-2xl bg-${banner.color}-500/10 border border-${banner.color}-500/30 flex items-center gap-4 text-xs`}>
          <div className={`p-2 rounded-xl bg-${banner.color}-500/20 text-${banner.color}-600 dark:text-${banner.color}-400`}>
            {banner.icon}
          </div>
          <div>
            <p className="font-bold text-slate-900 dark:text-slate-100">{banner.title}</p>
            <p className="text-slate-500 dark:text-slate-400">{banner.desc}</p>
          </div>
        </div>
      )}

      {/* Interactive Category Filter Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        {ALL_CATEGORIES.map((cat) => {
          const isCurrent = (activeCategory || 'All') === cat;
          return (
            <button
              key={cat}
              onClick={() => {
                if (setActiveCategory) setActiveCategory(cat);
                if (cat !== 'All' && activeFolder !== 'trash' && setActiveFolder) {
                  setActiveFolder('all');
                }
              }}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer shadow-xs ${
                isCurrent
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20 font-bold scale-[1.02]'
                  : 'bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-100'
              }`}
            >
              <span>{cat}</span>
            </button>
          );
        })}
      </div>

      {/* Top Toolbar */}
      <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-4">
        {/* Left: Bulk Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSelectAll}
            className="flex items-center gap-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900"
          >
            {selectedIds.length > 0 && selectedIds.length === emails.length ? (
              <CheckSquare className="w-4 h-4 text-blue-600" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            <span>Select All</span>
          </button>

          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2 border-l border-slate-200 dark:border-slate-800 pl-3">
              <span className="text-xs text-slate-500 font-medium">{selectedIds.length} selected</span>

              <button
                onClick={() => handleBulkAction('mark_read')}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Mark Read"
              >
                <MailOpen className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => handleBulkAction('mark_unread')}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800"
                title="Mark Unread"
              >
                <Mail className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => handleBulkAction('star')}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800 text-amber-500"
                title="Star selected"
              >
                <Star className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => handleBulkAction('mark_important')}
                className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800 text-orange-500"
                title="Mark Important"
              >
                <Bookmark className="w-3.5 h-3.5" />
              </button>

              {activeFolder === 'trash' ? (
                <>
                  <button
                    onClick={() => handleBulkAction('restore_inbox')}
                    className="px-2.5 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-900 text-xs font-semibold hover:bg-emerald-50 dark:hover:bg-emerald-950 text-emerald-600 flex items-center gap-1"
                    title="Restore to Inbox"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Restore</span>
                  </button>
                  <button
                    onClick={() => handleBulkAction('delete_permanent')}
                    className="px-2.5 py-1.5 rounded-lg border border-rose-200 dark:border-rose-900 text-xs font-semibold hover:bg-rose-50 dark:hover:bg-rose-950 text-rose-600 flex items-center gap-1"
                    title="Delete Permanently"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Permanently</span>
                  </button>
                </>
              ) : (
                <button
                  onClick={() => handleBulkAction('move_trash')}
                  className="p-1.5 rounded-lg border border-rose-200 dark:border-rose-900 text-xs font-medium hover:bg-rose-50 dark:hover:bg-rose-950 text-rose-600"
                  title="Move to Trash"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right: Active Filters, Sync Button & Sorting */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleManualSync}
            disabled={isSyncing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 dark:hover:bg-blue-900/60 border border-blue-200 dark:border-blue-800 rounded-xl transition-all shadow-xs disabled:opacity-50"
            title="Sync latest emails from Gmail"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Syncing...' : 'Sync Gmail'}</span>
          </button>

          <div className="flex items-center gap-1.5 border-l border-slate-200 dark:border-slate-800 pl-3 text-xs text-slate-500">
            <Filter className="w-3.5 h-3.5" />
            <span>Folder: <strong className="text-slate-800 dark:text-slate-200 capitalize">{activeFolder}</strong></span>
            {activeCategory !== 'All' && (
              <span className="ml-1 text-blue-600 dark:text-blue-400 font-bold">({activeCategory})</span>
            )}
          </div>

          <div className="flex items-center gap-1.5 border-l border-slate-200 dark:border-slate-800 pl-3">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent text-xs font-semibold text-slate-700 dark:text-slate-300 focus:outline-none cursor-pointer"
            >
              <option value="date_desc" className="bg-slate-900 text-white">Newest First</option>
              <option value="date_asc" className="bg-slate-900 text-white">Oldest First</option>
              <option value="confidence_desc" className="bg-slate-900 text-white">AI Confidence</option>
            </select>
          </div>
        </div>
      </div>

      {/* Email List View */}
      {isLoading || displayedEmails === null ? (
        <div className="glass-card p-12 flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-4 border-blue-600/20 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-xs text-slate-500">Loading {activeCategory !== 'All' ? activeCategory : ''} emails...</p>
        </div>
      ) : displayedEmails.length === 0 ? (
        <div className="glass-card p-12 text-center space-y-3">
          <Inbox className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto" />
          <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">No Emails Found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {activeFolder === 'snoozed'
              ? 'No emails are currently snoozed. Use the clock icon on any email to snooze it.'
              : activeFolder === 'important'
              ? 'No emails marked as Important. Use the bookmark icon to mark emails as important.'
              : `No emails match your current category filter (${activeCategory || 'All'}) or folder (${activeFolder}).`
            }
          </p>
        </div>
      ) : (
        (() => {
          const totalCount = displayedEmails?.length || 0;
          const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
          const safePage = Math.min(Math.max(1, currentPage), totalPages);
          const paginatedEmails = (displayedEmails || []).slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

          return (
            <div className="glass-card overflow-hidden">
              <div className="divide-y divide-slate-200/80 dark:divide-slate-800/80">
                {paginatedEmails.map((email) => {
                  const isSelected = selectedIds.includes(email.id);
                  return (
                    <div
                      key={email.id}
                      onClick={() => handleOpenEmail(email)}
                      className={`
                        flex items-center gap-3 px-4 py-3 cursor-pointer transition-all duration-150 group hover:bg-blue-50/50 dark:hover:bg-slate-900/60
                        ${!email.is_read ? 'bg-white dark:bg-slate-950 font-semibold' : 'bg-slate-50/40 dark:bg-slate-950/40 text-slate-600 dark:text-slate-400'}
                        ${isSelected ? 'bg-blue-50 dark:bg-blue-950/40' : ''}
                      `}
                    >
                      {/* Select Checkbox */}
                      <button
                        onClick={(e) => toggleSelectOne(email.id, e)}
                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 shrink-0"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 text-blue-600" />
                        ) : (
                          <Square className="w-4 h-4" />
                        )}
                      </button>

                      {/* Star Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleStar(email.id, email.is_starred);
                        }}
                        className={`p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors shrink-0 ${
                          email.is_starred ? 'text-amber-500' : 'text-slate-300 dark:text-slate-700'
                        }`}
                      >
                        <Star className={`w-4 h-4 ${email.is_starred ? 'fill-amber-500' : ''}`} />
                      </button>

                      {/* Important Button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleImportant(email.id, email.is_important);
                        }}
                        className={`p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors shrink-0 ${
                          email.is_important ? 'text-orange-500' : 'text-slate-300 dark:text-slate-700'
                        }`}
                        title={email.is_important ? "Important" : "Mark as Important"}
                      >
                        <Bookmark className={`w-4 h-4 ${email.is_important ? 'fill-orange-500' : ''}`} />
                      </button>

                      {/* Category Badge & Priority Highlight */}
                      <div className="shrink-0 flex items-center gap-1.5">
                        <CategoryBadge category={email.category} size="xs" />
                        {email.priority_highlight && (
                          <PriorityActionBadge highlight={email.priority_highlight} size="xs" />
                        )}
                      </div>

                      {/* Sender Name */}
                      <div className="w-32 shrink-0 truncate text-xs font-semibold text-slate-900 dark:text-slate-100">
                        {email.sender}
                      </div>

                      {/* Subject & Snippet Preview */}
                      <div className="flex-1 min-w-0 flex items-center gap-2 text-xs">
                        <span className="truncate font-semibold text-slate-900 dark:text-slate-100">
                          {email.subject}
                        </span>
                        <span className="text-slate-400 truncate hidden md:inline">
                          - {stripHtml(email.snippet || email.body).slice(0, 100)}
                        </span>
                      </div>

                      {/* Right side: Snooze badge, Confidence, Date, Snooze btn, Open btn */}
                      <div className="flex items-center gap-2 shrink-0 text-xs">
                        {/* Snooze badge */}
                        {email.is_snoozed && (
                          <span className="hidden sm:flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-600 text-[10px] font-bold">
                            <Clock className="w-2.5 h-2.5" />
                            {formatSnoozeLabel(email.snoozed_until)}
                          </span>
                        )}

                        <span className="font-mono text-[11px] font-bold text-blue-600 dark:text-blue-400">
                          {email.confidence}%
                        </span>
                        <span className="text-slate-400 text-[11px]">
                          {new Date(email.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                        </span>

                        {/* Snooze action button */}
                        <div className="relative" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => setSnoozePickerFor(snoozePickerFor === email.id ? null : email.id)}
                            className={`p-1.5 rounded-lg border transition-colors hidden group-hover:block ${
                              email.is_snoozed
                                ? 'bg-purple-500/10 border-purple-500/30 text-purple-500'
                                : 'border-slate-200 dark:border-slate-700 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                            }`}
                            title="Snooze"
                          >
                            <Clock className="w-3.5 h-3.5" />
                          </button>
                          {snoozePickerFor === email.id && (
                            <SnoozePicker
                              email={email}
                              onSnooze={handleSnooze}
                              onClose={() => setSnoozePickerFor(null)}
                            />
                          )}
                        </div>

                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenEmail(email);
                          }}
                          className="px-2.5 py-1 text-[11px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 dark:hover:bg-blue-900/60 border border-blue-200/80 dark:border-blue-800/80 rounded-lg transition-all"
                        >
                          Open
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination Bar */}
              {totalCount > PAGE_SIZE && (
                <div className="flex items-center justify-between px-4 py-3 bg-slate-50/80 dark:bg-slate-900/80 border-t border-slate-200/80 dark:border-slate-800/80 text-xs">
                  <span className="text-slate-500">
                    Showing <strong className="text-slate-800 dark:text-slate-200">{(safePage - 1) * PAGE_SIZE + 1}</strong> to <strong className="text-slate-800 dark:text-slate-200">{Math.min(safePage * PAGE_SIZE, totalCount)}</strong> of <strong className="text-slate-800 dark:text-slate-200">{totalCount}</strong> emails
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={safePage === 1}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 disabled:opacity-30 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium transition-colors cursor-pointer disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Prev</span>
                    </button>
                    <span className="px-2.5 py-1 font-semibold text-slate-700 dark:text-slate-300">
                      Page {safePage} of {totalPages}
                    </span>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={safePage >= totalPages}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-slate-800 disabled:opacity-30 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium transition-colors cursor-pointer disabled:cursor-not-allowed"
                    >
                      <span>Next</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })()
      )}
    </div>
  );
}
