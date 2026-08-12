import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { X, Send, Cpu, Sparkles, AlertCircle, FileText, CheckCircle2 } from 'lucide-react';
import API from '../services/api';
import CategoryBadge from './CategoryBadge';

export default function ComposeModal({ isOpen, onClose, onEmailSent }) {
  const [recipient, setRecipient] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  
  // Real-time live AI preview state
  const [aiPreview, setAiPreview] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Debounced live classification as the user types subject or body
  useEffect(() => {
    if (!subject.trim() && !body.trim()) {
      setAiPreview(null);
      return;
    }

    const timer = setTimeout(async () => {
      setIsAnalyzing(true);
      try {
        const res = await API.post('/emails/classify-text', { subject, body });
        setAiPreview(res.data.result);
      } catch (err) {
        console.warn("Live classification warning:", err);
      } finally {
        setIsAnalyzing(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [subject, body]);

  if (!isOpen) return null;

  const handleSend = async () => {
    if (!recipient.trim()) { setErrorMsg('Please enter a recipient email address.'); return; }
    if (!subject.trim())   { setErrorMsg('Please enter an email subject.'); return; }
    if (!body.trim())      { setErrorMsg('Please enter email body content.'); return; }

    // Basic email format check
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(recipient.trim())) {
      setErrorMsg('Please enter a valid email address (e.g. name@example.com).');
      return;
    }

    setIsSending(true);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const res = await API.post('/emails/send', { recipient, subject, body });
      setSuccessMsg(res.data.message || `Email sent to ${recipient}!`);
      setTimeout(() => {
        if (onEmailSent) onEmailSent(res.data.email);
        resetAndClose();
      }, 1800);
    } catch (err) {
      console.error('Failed to send email:', err);
      const serverMsg = err.response?.data?.message || 'Failed to send email. Please try again.';
      setErrorMsg(serverMsg);
    } finally {
      setIsSending(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!subject.trim() && !body.trim()) {
      setErrorMsg('Cannot save an empty draft.'); return;
    }
    setIsSavingDraft(true);
    setErrorMsg('');
    try {
      // Drafts are saved locally to the DB only (no SMTP send)
      const res = await API.post('/emails/send', {
        recipient: recipient || '(No recipient)',
        subject: subject || '(No subject)',
        body: body || '',
        folder: 'drafts'
      });
      setSuccessMsg('Draft saved successfully!');
      setTimeout(() => {
        if (onEmailSent) onEmailSent(res.data.email);
        resetAndClose();
      }, 1200);
    } catch (err) {
      setErrorMsg('Failed to save draft.');
    } finally {
      setIsSavingDraft(false);
    }
  };

  const resetAndClose = () => {
    setRecipient('');
    setSubject('');
    setBody('');
    setErrorMsg('');
    setSuccessMsg('');
    setAiPreview(null);
    onClose();
  };

  return ReactDOM.createPortal(
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-900/80 backdrop-blur-md animate-in fade-in duration-150"
      onClick={resetAndClose}
    >
      <div 
        className="w-full max-w-2xl glass-card bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 overflow-hidden shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col max-h-[90vh] relative z-[10000]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between bg-slate-50 dark:bg-slate-900">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
              <Send className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Compose New Email
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Sends a real email • AI classifies automatically
              </p>
            </div>
          </div>

          <button
            onClick={resetAndClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900 text-xs font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-900 text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Recipient */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              To (Recipient Email) <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              value={recipient}
              onChange={(e) => setRecipient(e.target.value)}
              placeholder="e.g. manager@company.com"
              className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-slate-800 dark:text-slate-200"
            />
          </div>

          {/* Subject */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Subject <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="e.g. Your Security Passcode: 882910"
              className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-slate-800 dark:text-slate-200"
            />
          </div>

          {/* Body */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Email Content / Body <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={6}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Type your message content here..."
              className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-slate-800 dark:text-slate-200 resize-none"
            />
          </div>

          {/* Real-time Live AI Classification Card */}
          <div className="p-3.5 rounded-2xl bg-blue-50/70 dark:bg-blue-950/40 border border-blue-200/80 dark:border-blue-800/60 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Cpu className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                  <span>Real-Time AI Classification Preview</span>
                  {isAnalyzing && <span className="text-[10px] text-blue-500 font-mono animate-pulse">Analyzing...</span>}
                </p>
                {aiPreview ? (
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Model detects category: <span className="font-bold text-blue-600 dark:text-blue-400">{aiPreview.category}</span> ({Math.round(aiPreview.confidence * 100)}% confidence)
                  </p>
                ) : (
                  <p className="text-[11px] text-slate-400">
                    Start typing a subject or body to see live category detection
                  </p>
                )}
              </div>
            </div>

            {aiPreview && (
              <div className="shrink-0">
                <CategoryBadge category={aiPreview.category} size="sm" />
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 border-t border-slate-200/80 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-900 flex items-center justify-between gap-3">
          <button
            onClick={handleSaveDraft}
            disabled={isSending || isSavingDraft || (!subject.trim() && !body.trim())}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-xl transition-all border border-slate-200 dark:border-slate-800 disabled:opacity-50"
          >
            <FileText className="w-4 h-4 text-slate-400" />
            <span>{isSavingDraft ? 'Saving...' : 'Save as Draft'}</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={resetAndClose}
              disabled={isSending}
              className="px-4 py-2 text-xs font-semibold text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>

            <button
              onClick={handleSend}
              disabled={isSending || isSavingDraft || !recipient || !subject || !body}
              className="flex items-center gap-2 px-5 py-2 text-xs font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl shadow-lg shadow-blue-500/25 transition-all disabled:opacity-50"
            >
              {isSending ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Delivering...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Send Email</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
