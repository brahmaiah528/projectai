import React, { useState } from 'react';
import API from '../services/api';
import CategoryBadge from '../components/CategoryBadge';
import { Cpu, Play, Sparkles, AlertCircle, BarChart2, CheckCircle2 } from 'lucide-react';

const SAMPLES = [
  {
    label: 'Bank Fraud Alert',
    subject: 'Urgent: Unauthorized Login Attempt Detected on your Chase Account',
    body: 'Dear Customer, we detected a login to your Chase online banking from a new IP address in Russia. If this was not you, please verify your identity immediately or your card will be locked within 12 hours.'
  },
  {
    label: 'Job Offer',
    subject: 'Job Offer: Senior Full Stack Software Engineer at TechCorp',
    body: 'We are pleased to offer you the position of Senior Software Developer at TechCorp. Please review the attached compensation offer letter and start date confirmation.'
  },
  {
    label: 'Exam Admit Card',
    subject: 'Admit Card Released: National Graduate Entrance Examination 2026',
    body: 'Dear Candidate, your official admit card for the upcoming entrance examination is now available for download on the student portal. Exam starts at 9:00 AM.'
  },
  {
    label: 'Crypto Spam',
    subject: 'CONGRATULATIONS! You won 2.5 Ethereum Deposit Immediately!!',
    body: 'You have been selected as lucky winner of 2.5 ETH cash prize. Click here now to enter wallet seed phrase and claim your tokens before offer expires!'
  },
  {
    label: 'Security Alert',
    subject: 'Google Account Security Alert: New Sign-in',
    body: 'We noticed a new sign-in to your Google Account on a Windows device. If this was you, you don\'t need to do anything. If not, check your account activity.'
  },
  {
    label: 'Order Purchase',
    subject: 'Receipt #94821 for your Apple Store purchase of $999.00',
    body: 'Thank you for your order! Your MacBook Air purchase has been confirmed and billed to Visa ending in 5521. Package will ship via FedEx.'
  }
];

export default function ClassifierLabPage() {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [selectedModel, setSelectedModel] = useState('Multinomial Naive Bayes');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleClassify = async () => {
    if (!subject && !body) return;
    setIsLoading(true);
    try {
      const res = await API.post('/emails/classify-text', {
        subject,
        body,
        model_name: selectedModel
      });
      setResult(res.data.result);
    } catch (err) {
      console.error("Classification failed:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadSample = (s) => {
    setSubject(s.subject);
    setBody(s.body);
    setResult(null);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-card p-6 border bg-gradient-to-r from-purple-900/90 via-slate-900 to-blue-950 text-white">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-xl bg-purple-500/20 border border-purple-400/20 text-purple-300">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">AI Classification Testing Lab</h2>
            <p className="text-xs text-slate-300">
              Test custom email subjects and body text against trained Machine Learning models in real-time.
            </p>
          </div>
        </div>

        {/* Quick Sample Presets */}
        <div className="mt-4 pt-4 border-t border-white/10 flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-purple-300">Load Test Preset:</span>
          {SAMPLES.map((s, i) => (
            <button
              key={i}
              onClick={() => loadSample(s)}
              className="px-2.5 py-1 text-xs font-medium bg-white/10 hover:bg-white/20 text-white rounded-lg border border-white/10 transition-all"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Input Form (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Email Text Content</h3>
              
              {/* Model Choice Dropdown */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400 font-medium">Model:</span>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="px-2 py-1 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg font-semibold text-slate-800 dark:text-slate-200 focus:outline-none"
                >
                  <option value="Multinomial Naive Bayes">Multinomial Naive Bayes</option>
                  <option value="Logistic Regression">Logistic Regression</option>
                  <option value="Random Forest">Random Forest</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Subject Line
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Urgent: Account Password Reset Required"
                className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Email Body Text
              </label>
              <textarea
                rows={6}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Paste email text here..."
                className="w-full px-3.5 py-2 text-sm bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>

            <button
              onClick={handleClassify}
              disabled={isLoading || (!subject && !body)}
              className="w-full py-3 px-4 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-purple-500/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {isLoading ? (
                <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Run AI Email Categorization</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Output Results Panel (5 Cols) */}
        <div className="lg:col-span-5">
          <div className="glass-card p-6 min-h-[400px] flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-4 flex items-center justify-between">
                <span>Prediction Output</span>
                {result && <span className="text-xs font-mono text-purple-500 font-semibold">{result.model_used}</span>}
              </h3>

              {!result ? (
                <div className="py-16 text-center space-y-3">
                  <BarChart2 className="w-12 h-12 text-slate-300 dark:text-slate-700 mx-auto" />
                  <p className="text-xs text-slate-400 max-w-xs mx-auto">
                    Enter text or pick a sample preset on the left and click "Run AI Email Categorization" to inspect live category probability distribution.
                  </p>
                </div>
              ) : (
                <div className="space-y-6 animate-in fade-in duration-200">
                  {/* Primary Prediction Result */}
                  <div className="p-4 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-center space-y-2">
                    <p className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-wider">
                      Predicted Category
                    </p>
                    <div className="inline-block">
                      <CategoryBadge category={result.category} size="lg" />
                    </div>
                    <div className="pt-1">
                      <p className="text-2xl font-black text-slate-900 dark:text-slate-100">
                        {round(result.confidence * 100)}% Confidence
                      </p>
                    </div>
                  </div>

                  {/* Probabilities Breakdown List */}
                  <div>
                    <p className="text-xs font-bold text-slate-700 dark:text-slate-300 mb-3">
                      Category Probability Spectrum
                    </p>
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {Object.entries(result.probabilities || {})
                        .sort(([, a], [, b]) => b - a)
                        .map(([cat, prob]) => {
                          const percent = Math.round(prob * 100);
                          return (
                            <div key={cat} className="space-y-1">
                              <div className="flex justify-between text-xs font-medium">
                                <span className="text-slate-700 dark:text-slate-300">{cat}</span>
                                <span className="font-mono text-slate-500">{percent}%</span>
                              </div>
                              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-full rounded-full transition-all duration-300 ${
                                    cat === result.category ? 'bg-purple-600' : 'bg-slate-400/40'
                                  }`}
                                  style={{ width: `${percent}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function round(val) {
  return Math.round(val * 10) / 10;
}
