import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import API from '../services/api';
import { 
  X, Star, Trash2, Mail, MailOpen, Cpu, ShieldCheck, 
  Calendar, User, ArrowLeft, Send, CheckCircle2, CornerUpLeft 
} from 'lucide-react';
import CategoryBadge, { PriorityActionBadge } from './CategoryBadge';

export default function EmailModal({ email, onClose, onToggleStar, onToggleRead, onDelete }) {
  const [replyText, setReplyText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sentSuccess, setSentSuccess] = useState(false);

  if (!email) return null;

  const handleSendReply = async () => {
    if (!replyText.trim()) return;
    setIsSending(true);
    try {
      await API.post('/emails/send', {
        recipient: email.sender_email || email.sender,
        subject: `Re: ${email.subject}`,
        body: replyText
      });
      setSentSuccess(true);
      setReplyText('');
      setTimeout(() => setSentSuccess(false), 4000);
    } catch (err) {
      console.error("Failed to send reply:", err);
    } finally {
      setIsSending(false);
    }
  };

  return ReactDOM.createPortal(
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-md animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-3xl glass-card bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col max-h-[90vh] relative z-[10000]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header toolbar */}
        <div className="px-6 py-4 border-b border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between bg-slate-50 dark:bg-slate-900">
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <CategoryBadge category={email.category} size="lg" />
            {email.priority_highlight && (
              <PriorityActionBadge highlight={email.priority_highlight} size="sm" />
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onToggleStar && onToggleStar(email.id, email.is_starred)}
              className={`p-2 rounded-xl border transition-colors ${
                email.is_starred 
                  ? 'bg-amber-500/10 border-amber-500/30 text-amber-500' 
                  : 'border-slate-200 dark:border-slate-800 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
              title={email.is_starred ? "Starred" : "Star message"}
            >
              <Star className={`w-4 h-4 ${email.is_starred ? 'fill-amber-500' : ''}`} />
            </button>

            <button
              onClick={() => onToggleRead && onToggleRead(email.id, email.is_read)}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title={email.is_read ? "Mark as unread" : "Mark as read"}
            >
              {email.is_read ? <Mail className="w-4 h-4" /> : <MailOpen className="w-4 h-4" />}
            </button>

            <button
              onClick={() => onDelete && onDelete(email.id)}
              className="p-2 rounded-xl border border-rose-200 dark:border-rose-900/50 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
              title={email.folder === 'trash' ? "Delete Permanently" : "Move to Trash"}
            >
              <Trash2 className="w-4 h-4" />
            </button>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Email Header Info */}
        <div className="p-6 space-y-4 border-b border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-950">
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 leading-snug">
            {email.subject}
          </h2>

          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white font-bold flex items-center justify-center text-sm shadow-md">
                {email.sender ? email.sender[0].toUpperCase() : 'U'}
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <span>{email.sender}</span>
                  <span className="text-xs font-normal text-slate-400">&lt;{email.sender_email}&gt;</span>
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  To: <span className="font-medium">{email.recipient}</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <Calendar className="w-3.5 h-3.5" />
              <span>{email.date ? new Date(email.date).toLocaleString() : 'Just now'}</span>
            </div>
          </div>

          {/* AI Categorization Confidence Banner */}
          <div className="p-3 rounded-xl bg-blue-50/80 dark:bg-blue-950/40 border border-blue-200/80 dark:border-blue-800/60 flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <Cpu className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <div>
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  AI Classified as <span className="text-blue-600 dark:text-blue-400">{email.category}</span>
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  TF-IDF + Multinomial Naive Bayes Model
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-24 bg-slate-200 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-blue-600 h-full rounded-full transition-all duration-300"
                  style={{ width: `${email.confidence || 90}%` }}
                />
              </div>
              <span className="text-xs font-bold text-blue-600 dark:text-blue-400">
                {email.confidence || 90}%
              </span>
            </div>
          </div>
        </div>

        {/* Email Body Content */}
        <div className="overflow-y-auto flex-1 bg-white dark:bg-slate-950">
          <EmailBodyRenderer rawBody={email.body} />
        </div>

        {/* Immediate Quick Reply Section */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 space-y-2">
          {sentSuccess && (
            <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-xs font-semibold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>Reply sent successfully to {email.sender_email || email.sender}!</span>
            </div>
          )}

          <div className="flex items-start gap-2">
            <CornerUpLeft className="w-4 h-4 text-slate-400 mt-2 shrink-0" />
            <div className="flex-1 space-y-2">
              <textarea
                rows={2}
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                placeholder={`Type immediate reply to ${email.sender}...`}
                className="w-full p-2.5 text-xs bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 dark:text-slate-100"
              />
              <div className="flex justify-end">
                <button
                  onClick={handleSendReply}
                  disabled={isSending || !replyText.trim()}
                  className="px-4 py-1.5 text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow-md transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  {isSending ? (
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <><Send className="w-3.5 h-3.5" /><span>Send Immediate Reply</span></>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}

function EmailBodyRenderer({ rawBody }) {
  if (!rawBody || !rawBody.trim()) {
    return (
      <div className="p-6 text-slate-400 italic text-sm text-center">
        No content in this message.
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

  const looksLikeHtml = /<[a-z]/i.test(html);

  if (!looksLikeHtml) {
    return (
      <div className="whitespace-pre-wrap text-slate-800 dark:text-slate-200 leading-relaxed text-sm p-6">
        {rawBody}
      </div>
    );
  }

  const fullHtmlDoc = /<html/i.test(html) ? html : `<!DOCTYPE html><html><head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1"/>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
             color: #1e293b; margin: 0; padding: 16px; font-size: 14px; line-height: 1.6; background: #fff; }
      img  { max-width: 100% !important; height: auto !important; display: block; margin: 8px 0; }
      table { max-width: 100% !important; }
      a { color: #2563eb; }
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
