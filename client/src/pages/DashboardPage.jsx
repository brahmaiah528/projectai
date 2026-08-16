import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import API from '../services/api';
import { 
  Mail, AlertTriangle, Star, Tag, Landmark, Briefcase, 
  GraduationCap, ShoppingBag, Users, User, RefreshCw, Cpu, Activity, ArrowRight, ShieldCheck, Zap 
} from 'lucide-react';
import CategoryBadge, { PriorityActionBadge } from '../components/CategoryBadge';
import EmailModal from '../components/EmailModal';
import { 
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend 
} from 'recharts';

const CATEGORY_COLORS = {
  'Immediate Reply': '#dc2626',
  Spam: '#ef4444',
  Important: '#f59e0b',
  Promotions: '#a855f7',
  Banking: '#10b981',
  Jobs: '#3b82f6',
  Examinations: '#6366f1',
  Purchases: '#14b8a6',
  Social: '#06b6d4',
  Personal: '#ec4899',
  Updates: '#0284c7',
  Others: '#64748b'
};

export default function DashboardPage({ setActiveCategory, setActiveFolder }) {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [activeEmail, setActiveEmail] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async (silent = false) => {
    if (silent) setIsBgRefresh(true);
    setError('');
    try {
      const res = await API.get('/analytics/dashboard');
      if (res.data) {
        setStats(res.data);
      }
    } catch (err) {
      console.error("Failed to load dashboard stats:", err);
      setError(err.response?.data?.message || 'Unable to connect to analytics server. Please refresh.');
    } finally {
      setIsLoading(false);
      setIsBgRefresh(false);
    }
  };

  const handleOpenEmail = async (email) => {
    if (!email) return;
    try {
      const res = await API.get(`/emails/${email.id}`);
      setActiveEmail(res.data.email || email);
    } catch (_) {
      setActiveEmail(email);
    }
  };

  const handleCardClick = (cardLabel) => {
    if (cardLabel === 'Total Emails') {
      if (setActiveCategory) setActiveCategory('All');
      if (setActiveFolder) setActiveFolder('all');
    } else if (cardLabel === 'Spam Emails') {
      if (setActiveCategory) setActiveCategory('All');
      if (setActiveFolder) setActiveFolder('spam');
    } else {
      // For any specific category, search ALL folders so we don't miss emails
      if (setActiveCategory) setActiveCategory(cardLabel);
      if (setActiveFolder) setActiveFolder('all');
    }
    navigate('/inbox');
  };

  const handleToggleStar = async (emailId, currentStarred) => {
    try {
      await API.patch(`/emails/${emailId}`, { is_starred: !currentStarred });
      if (activeEmail && activeEmail.id === emailId) {
        setActiveEmail(prev => ({ ...prev, is_starred: !currentStarred }));
      }
    } catch (err) {
      console.error("Failed to star email:", err);
    }
  };

  const handleToggleRead = async (emailId, currentRead) => {
    try {
      await API.patch(`/emails/${emailId}`, { is_read: !currentRead });
      if (activeEmail && activeEmail.id === emailId) {
        setActiveEmail(prev => ({ ...prev, is_read: !currentRead }));
      }
    } catch (err) {
      console.error("Failed to update read status:", err);
    }
  };

  const handleDelete = async (emailId) => {
    try {
      await API.delete(`/emails/${emailId}`);
      setActiveEmail(null);
      fetchDashboardStats();
    } catch (err) {
      console.error("Failed to delete email:", err);
    }
  };

  // Skeleton card component shown while data loads
  const SkeletonCard = () => (
    <div className="glass-card p-5 animate-pulse">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-xl bg-slate-200 dark:bg-slate-800" />
        <div className="h-3 w-24 rounded bg-slate-200 dark:bg-slate-800" />
      </div>
      <div className="h-7 w-16 rounded bg-slate-200 dark:bg-slate-800" />
    </div>
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="glass-card p-6 animate-pulse">
          <div className="h-6 w-48 rounded bg-slate-200 dark:bg-slate-800 mb-2" />
          <div className="h-4 w-72 rounded bg-slate-200 dark:bg-slate-800" />
        </div>
        {/* Stat cards skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({length: 8}).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        {/* Chart skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-card p-6 animate-pulse">
            <div className="h-4 w-32 rounded bg-slate-200 dark:bg-slate-800 mb-4" />
            <div className="h-52 rounded-xl bg-slate-100 dark:bg-slate-900" />
          </div>
          <div className="glass-card p-6 animate-pulse">
            <div className="h-4 w-32 rounded bg-slate-200 dark:bg-slate-800 mb-4" />
            <div className="h-52 rounded-xl bg-slate-100 dark:bg-slate-900" />
          </div>
        </div>
      </div>
    );
  }

  if (!isLoading && !stats) {
    return (
      <div className="glass-card p-12 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto" />
        <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
          {error || 'Unable to load dashboard data'}
        </h3>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          Please check your connection and try reloading the analytics.
        </p>
        <button
          onClick={() => {
            setIsLoading(true);
            fetchDashboardStats();
          }}
          className="px-5 py-2 text-xs font-bold text-white bg-blue-600 rounded-xl hover:bg-blue-500 transition-colors shadow-md shadow-blue-500/20"
        >
          Try Again
        </button>
      </div>
    );
  }

  const s = stats?.summary || {};
  const pieData = stats?.category_pie || [];
  const dailyStats = stats?.daily_stats || [];

  const cards = [
    { label: 'Immediate Reply', categoryKey: 'Immediate Reply', count: s.immediate_reply || 0, icon: Zap, color: 'text-red-500 bg-red-500/10 font-bold' },
    { label: 'Total Emails', categoryKey: 'Total Emails', count: s.total, icon: Mail, color: 'text-blue-500 bg-blue-500/10' },
    { label: 'Spam Emails', categoryKey: 'Spam Emails', count: s.spam, icon: AlertTriangle, color: 'text-rose-500 bg-rose-500/10' },
    { label: 'Important', categoryKey: 'Important', count: s.important, icon: Star, color: 'text-amber-500 bg-amber-500/10' },
    { label: 'Banking', categoryKey: 'Banking', count: s.banking, icon: Landmark, color: 'text-emerald-500 bg-emerald-500/10' },
    { label: 'Jobs', categoryKey: 'Jobs', count: s.jobs, icon: Briefcase, color: 'text-blue-500 bg-blue-500/10' },
    { label: 'Examinations', categoryKey: 'Examinations', count: s.examinations, icon: GraduationCap, color: 'text-indigo-500 bg-indigo-500/10' },
    { label: 'Purchases', categoryKey: 'Purchases', count: s.purchases, icon: ShoppingBag, color: 'text-teal-500 bg-teal-500/10' },
    { label: 'Promotions', categoryKey: 'Promotions', count: s.promotions, icon: Tag, color: 'text-purple-500 bg-purple-500/10' },
    { label: 'Social', categoryKey: 'Social', count: s.social, icon: Users, color: 'text-cyan-500 bg-cyan-500/10' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-card p-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-gradient-to-r from-blue-900/40 via-indigo-900/30 to-purple-900/30">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-blue-400" />
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              AI Content Categorization Dashboard
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Real-time classification using Multinomial Naive Bayes Model (Accuracy: 94.0%)
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/inbox')}
            className="flex items-center gap-2 px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 rounded-xl transition-all shadow-md shadow-blue-500/20"
          >
            <Mail className="w-4 h-4" />
            <span>Open Full Inbox</span>
          </button>
          <button
            onClick={fetchDashboardStats}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 hover:bg-blue-100 dark:hover:bg-blue-900/60 border border-blue-200 dark:border-blue-800 rounded-xl transition-all shadow-sm"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Clickable Category Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {cards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div 
              key={idx} 
              onClick={() => handleCardClick(card.categoryKey)}
              className="glass-card p-4 space-y-2 hover:scale-[1.02] cursor-pointer transition-all duration-200 group border border-slate-200/80 dark:border-slate-800/80 hover:border-blue-500/50"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  {card.label}
                </span>
                <div className={`p-2 rounded-xl ${card.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="flex items-baseline justify-between pt-1">
                <span className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">
                  {card.count || 0}
                </span>
                <span className="text-[10px] text-blue-500 font-semibold flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                  View <ArrowRight className="w-3 h-3 ml-0.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Distribution Pie Chart */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-500" />
              <span>Category Distribution</span>
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">{pieData.length} active classes</span>
          </div>

          <div className="h-64 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={CATEGORY_COLORS[entry.name] || '#64748b'} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#0f172a', 
                    borderColor: '#334155', 
                    borderRadius: '0.75rem',
                    color: '#fff',
                    fontSize: '12px'
                  }} 
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Category Pill Legend */}
          <div className="flex flex-wrap gap-1.5 pt-2">
            {pieData.map((p) => (
              <span 
                key={p.name}
                onClick={() => handleCardClick(p.name)}
                className="px-2 py-1 text-[10px] font-bold rounded-lg cursor-pointer hover:opacity-80 transition-opacity text-white shadow-xs"
                style={{ backgroundColor: CATEGORY_COLORS[p.name] || '#64748b' }}
              >
                {p.name}: {p.value}
              </span>
            ))}
          </div>
        </div>

        {/* Daily Processing Trend Bar Chart */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-emerald-500" />
              <span>7-Day Classification Trend</span>
            </h3>
            <span className="text-[11px] text-slate-400 font-mono">Daily volume</span>
          </div>

          <div className="h-64 w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" minWidth={100} minHeight={200}>
              <BarChart data={dailyStats}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={11} />
                <YAxis stroke="#94a3b8" fontSize={11} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#0f172a', 
                    borderColor: '#334155', 
                    borderRadius: '0.75rem',
                    color: '#fff',
                    fontSize: '12px'
                  }} 
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                <Bar dataKey="total" name="Total Emails" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="spam" name="Spam Filtered" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Classified Emails Table */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            Recent Classified Emails
          </h3>
          <span className="text-xs text-blue-500 font-medium cursor-pointer" onClick={() => navigate('/inbox')}>
            View All Inbox &rarr;
          </span>
        </div>

        {stats?.recent_emails && stats.recent_emails.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100/60 dark:bg-slate-900/60 uppercase text-[10px] font-bold text-slate-400">
                <tr>
                  <th className="py-2.5 px-4">Sender</th>
                  <th className="py-2.5 px-4">Subject</th>
                  <th className="py-2.5 px-4">Category</th>
                  <th className="py-2.5 px-4">Confidence</th>
                  <th className="py-2.5 px-4">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800/80">
                {stats.recent_emails.map((e) => (
                  <tr 
                    key={e.id} 
                    onClick={() => handleOpenEmail(e)}
                    className="hover:bg-slate-50/50 dark:hover:bg-slate-900/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">{e.sender}</td>
                    <td className="py-3 px-4 max-w-xs truncate font-medium">{e.subject}</td>
                    <td className="py-3 px-4 flex items-center gap-2">
                      <CategoryBadge category={e.category} size="xs" />
                      {e.priority_highlight && <PriorityActionBadge highlight={e.priority_highlight} size="xs" />}
                    </td>
                    <td className="py-3 px-4 font-bold text-blue-600 dark:text-blue-400">{e.confidence}%</td>
                    <td className="py-3 px-4 text-slate-400">{new Date(e.date).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center space-y-2">
            <p className="text-xs text-slate-400">Click below to open your full inbox or browse by category.</p>
            <button
              onClick={() => navigate('/inbox')}
              className="px-4 py-1.5 text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 rounded-xl hover:bg-blue-100 dark:hover:bg-blue-900/60 transition-colors"
            >
              Open Full Inbox &rarr;
            </button>
          </div>
        )}
      </div>

      {/* Modal reader when a recent email row is clicked on dashboard */}
      {activeEmail && (
        <EmailModal
          email={activeEmail}
          onClose={() => setActiveEmail(null)}
          onToggleStar={handleToggleStar}
          onToggleRead={handleToggleRead}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
