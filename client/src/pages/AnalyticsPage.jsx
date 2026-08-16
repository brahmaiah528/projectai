import React, { useState, useEffect } from 'react';
import API from '../services/api';
import { BarChart3, Award, Zap, ShieldCheck, Database, Layers } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, Legend 
} from 'recharts';

export default function AnalyticsPage() {
  const [modelData, setModelData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchModelMetrics();
  }, []);

  const fetchModelMetrics = async () => {
    try {
      const res = await API.get('/analytics/models');
      setModelData(res.data.metrics);
    } catch (err) {
      console.error("Failed to load model metrics:", err);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="glass-card p-6 animate-pulse bg-gradient-to-r from-emerald-900/90 via-slate-900 to-teal-950">
          <div className="h-6 w-64 rounded bg-emerald-800/60 mb-2" />
          <div className="h-4 w-96 rounded bg-emerald-800/40" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({length: 3}).map((_, i) => (
            <div key={i} className="glass-card p-5 animate-pulse">
              <div className="h-3 w-24 rounded bg-slate-200 dark:bg-slate-800 mb-3" />
              <div className="h-8 w-20 rounded bg-slate-200 dark:bg-slate-800" />
            </div>
          ))}
        </div>
        <div className="glass-card p-6 animate-pulse">
          <div className="h-4 w-40 rounded bg-slate-200 dark:bg-slate-800 mb-4" />
          <div className="h-64 rounded-xl bg-slate-100 dark:bg-slate-900" />
        </div>
      </div>
    );
  }

  const metrics = modelData?.metrics || {};
  const bestModel = modelData?.best_model || 'Multinomial Naive Bayes';

  // Prepare chart data for model comparison
  const chartData = Object.keys(metrics).map((modelName) => {
    const m = metrics[modelName];
    return {
      name: modelName,
      Accuracy: round(m.accuracy * 100),
      Precision: round(m.precision * 100),
      Recall: round(m.recall * 100),
      F1Score: round(m.f1_score * 100),
    };
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="glass-card p-6 border bg-gradient-to-r from-emerald-900/90 via-slate-900 to-teal-950 text-white">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-xl bg-emerald-500/20 border border-emerald-400/20 text-emerald-300">
            <BarChart3 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Machine Learning Model Performance & Analytics</h2>
            <p className="text-xs text-slate-300">
              Comparative benchmark evaluation of TF-IDF feature vectorization paired with 3 Machine Learning algorithms.
            </p>
          </div>
        </div>

        {/* Best Model Badge */}
        <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-300">
            <Award className="w-4 h-4 text-amber-400" />
            <span>Optimal Production Classifier: <strong className="text-white font-bold">{bestModel}</strong></span>
          </div>
          <span className="text-xs font-mono text-slate-300">
            Training Samples: {modelData?.dataset_size || 250} | Train-Test Split: 80/20
          </span>
        </div>
      </div>

      {/* Model Benchmark Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Object.keys(metrics).map((mName) => {
          const m = metrics[mName];
          const isBest = mName === bestModel;
          return (
            <div 
              key={mName} 
              className={`glass-card p-5 border relative overflow-hidden transition-all ${
                isBest ? 'ring-2 ring-emerald-500 shadow-lg shadow-emerald-500/10' : ''
              }`}
            >
              {isBest && (
                <span className="absolute top-3 right-3 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-emerald-500 text-white">
                  Best Accuracy
                </span>
              )}
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-3">{mName}</h3>
              
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Accuracy</span>
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">{round(m.accuracy * 100)}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Precision</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{round(m.precision * 100)}%</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100 dark:border-slate-800">
                  <span className="text-slate-500">Recall</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{round(m.recall * 100)}%</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">F1 Score</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">{round(m.f1_score * 100)}%</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Comparison Chart */}
      <div className="glass-card p-6">
        <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-4">
          Algorithm Metric Comparison (%)
        </h3>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
              <YAxis domain={[50, 100]} stroke="#94a3b8" fontSize={12} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '12px', color: '#fff', fontSize: '12px' }} 
              />
              <Legend />
              <Bar dataKey="Accuracy" fill="#10b981" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Precision" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Recall" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="F1Score" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Table */}
      <div className="glass-card p-6">
        <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 mb-4">
          Detailed Performance Summary
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
            <thead className="bg-slate-100/60 dark:bg-slate-900/60 uppercase text-[10px] font-bold text-slate-400">
              <tr>
                <th className="py-3 px-4">Model Algorithm</th>
                <th className="py-3 px-4">Accuracy</th>
                <th className="py-3 px-4">Precision (Weighted)</th>
                <th className="py-3 px-4">Recall (Weighted)</th>
                <th className="py-3 px-4">F1 Score (Weighted)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800/80">
              {Object.keys(metrics).map((mName) => {
                const m = metrics[mName];
                return (
                  <tr key={mName} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/40">
                    <td className="py-3 px-4 font-bold text-slate-900 dark:text-slate-100">{mName}</td>
                    <td className="py-3 px-4 font-bold text-emerald-600 dark:text-emerald-400">{round(m.accuracy * 100)}%</td>
                    <td className="py-3 px-4">{round(m.precision * 100)}%</td>
                    <td className="py-3 px-4">{round(m.recall * 100)}%</td>
                    <td className="py-3 px-4 font-semibold text-slate-800 dark:text-slate-200">{round(m.f1_score * 100)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function round(val) {
  return Math.round(val * 10) / 10;
}
