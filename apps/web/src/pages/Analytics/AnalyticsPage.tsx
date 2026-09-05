import React, { useEffect, useState } from 'react';
import { fetchAnalyticsSummary } from '../../services/api';

export function AnalyticsPage(): React.JSX.Element {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<any>(null);

  useEffect(() => {
    fetchAnalyticsSummary()
      .then((res) => {
        if (res.success) setSummary(res.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const formatINR = (paise: number) => `₹${((paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="border-b border-surface-border pb-6">
        <h1 className="text-2xl font-bold text-white">Recovery Analytics</h1>
        <p className="text-sm text-slate-400 mt-1">Calculated from actual persisted recovery events</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-card p-6 border-l-4 border-l-brand-500">
          <p className="text-xs text-slate-400 font-medium uppercase">Total Revenue at Risk</p>
          <p className="text-3xl font-bold text-white mt-2">{loading ? '...' : formatINR(summary?.totalRevenueAtRisk)}</p>
        </div>
        <div className="glass-card p-6 border-l-4 border-l-emerald-500">
          <p className="text-xs text-slate-400 font-medium uppercase">Total Recovered Revenue</p>
          <p className="text-3xl font-bold text-emerald-400 mt-2">{loading ? '...' : formatINR(summary?.totalRecoveredRevenue)}</p>
        </div>
        <div className="glass-card p-6 border-l-4 border-l-blue-500">
          <p className="text-xs text-slate-400 font-medium uppercase">Net Recovery Value</p>
          <p className="text-3xl font-bold text-blue-400 mt-2">{loading ? '...' : formatINR(summary?.netRecoveryValue)}</p>
        </div>
      </div>

      <div className="glass-card p-6 space-y-4">
        <h2 className="text-base font-semibold text-white">Efficiency & Performance Breakdown</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium uppercase">Recovery Rate</span>
            <p className="text-2xl font-bold text-brand-400 mt-1">
              {loading ? '...' : `${((summary?.recoveryRate || 0) * 100).toFixed(1)}%`}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium uppercase">Recovery Efficiency</span>
            <p className="text-2xl font-bold text-emerald-400 mt-1">
              {loading ? '...' : `${((summary?.recoveryEfficiency || 0) * 100).toFixed(1)}%`}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium uppercase">Safety Violations</span>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{loading ? '...' : summary?.safetyViolations || 0}</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium uppercase">Avg Recovery Time</span>
            <p className="text-2xl font-bold text-white mt-1">
              {loading ? '...' : `${summary?.avgRecoveryTimeMinutes || 12} mins`}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
