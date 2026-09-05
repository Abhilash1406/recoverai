import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { triggerDemoSuite, fetchAnalyticsSummary, fetchRecoveryCases } from '../../services/api';

export function DashboardPage(): React.JSX.Element {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [runningDemo, setRunningDemo] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sumRes, casesRes] = await Promise.all([fetchAnalyticsSummary(), fetchRecoveryCases()]);
      if (sumRes.success) setSummary(sumRes.data);
      if (casesRes.success) setCases(casesRes.data);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunDemo = async () => {
    try {
      setRunningDemo(true);
      await triggerDemoSuite();
      await loadData();
    } catch (err) {
      console.error(err);
    } finally {
      setRunningDemo(false);
    }
  };

  const formatINR = (paise: number) => {
    return `₹${((paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header & Demo Trigger */}
      <div className="flex items-center justify-between border-b border-surface-border pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Recovery Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time Risk-Aware Autonomous Revenue Recovery Engine
          </p>
        </div>
        <button
          onClick={handleRunDemo}
          disabled={runningDemo}
          className="px-5 py-2.5 bg-gradient-to-r from-brand-500 to-blue-600 hover:from-brand-600 hover:to-blue-700 text-white font-medium text-sm rounded-lg shadow-lg shadow-brand-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
        >
          {runningDemo ? 'Running Seed=42 Suite...' : '⚡ Trigger Seed=42 Demo Suite'}
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card p-5 border-l-4 border-l-amber-500">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Revenue at Risk</p>
          <p className="text-2xl font-bold text-white mt-2">
            {loading ? '...' : formatINR(summary?.totalRevenueAtRisk)}
          </p>
          <p className="text-xs text-slate-500 mt-1">{summary?.totalCases || 0} failed transactions</p>
        </div>

        <div className="glass-card p-5 border-l-4 border-l-emerald-500">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Recovered Revenue</p>
          <p className="text-2xl font-bold text-emerald-400 mt-2">
            {loading ? '...' : formatINR(summary?.totalRecoveredRevenue)}
          </p>
          <p className="text-xs text-emerald-500/80 mt-1">
            Efficiency: {loading ? '...' : `${((summary?.recoveryEfficiency || 0) * 100).toFixed(1)}%`}
          </p>
        </div>

        <div className="glass-card p-5 border-l-4 border-l-brand-500">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Recovery Rate</p>
          <p className="text-2xl font-bold text-brand-400 mt-2">
            {loading ? '...' : `${((summary?.recoveryRate || 0) * 100).toFixed(1)}%`}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {summary?.recoveredCases || 0} / {summary?.totalCases || 0} cases recovered
          </p>
        </div>

        <div className="glass-card p-5 border-l-4 border-l-blue-500">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Net Recovery Value</p>
          <p className="text-2xl font-bold text-blue-400 mt-2">
            {loading ? '...' : formatINR(summary?.netRecoveryValue)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Safety Violations: <span className="text-emerald-400 font-semibold">{summary?.safetyViolations || 0}</span>
          </p>
        </div>
      </div>

      {/* Visual Recovery Pipeline */}
      <div className="glass-card p-6">
        <h2 className="text-base font-semibold text-white mb-4">Visual Recovery Pipeline</h2>
        <div className="grid grid-cols-5 gap-3 text-center">
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium uppercase">1. Detected</span>
            <p className="text-xl font-bold text-white mt-1">
              {cases.filter((c) => c.state === 'DETECTED').length}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium uppercase">2. Analyzing</span>
            <p className="text-xl font-bold text-blue-400 mt-1">
              {cases.filter((c) => c.state === 'ANALYZING').length}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium uppercase">3. Decision Ready</span>
            <p className="text-xl font-bold text-brand-400 mt-1">
              {cases.filter((c) => c.state === 'DECISION_READY' || c.state === 'ACTION_EXECUTED').length}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-emerald-950/40 border border-emerald-900/50">
            <span className="text-xs text-emerald-400 font-medium uppercase">4. Recovered</span>
            <p className="text-xl font-bold text-emerald-400 mt-1">
              {cases.filter((c) => c.state === 'RECOVERED').length}
            </p>
          </div>
          <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-900/50">
            <span className="text-xs text-rose-400 font-medium uppercase">5. Stopped / Policy</span>
            <p className="text-xl font-bold text-rose-400 mt-1">
              {cases.filter((c) => c.state === 'STOPPED' || c.state === 'MERCHANT_REVIEW').length}
            </p>
          </div>
        </div>
      </div>

      {/* Active Recovery Cases Table */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white">Active Recovery Cases</h2>
          <button
            onClick={() => navigate('/recovery')}
            className="text-xs font-medium text-brand-400 hover:text-brand-300 transition-colors"
          >
            View All Cases →
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs text-slate-400 uppercase border-b border-surface-border">
              <tr>
                <th className="px-4 py-3">Case ID</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Failure Category</th>
                <th className="px-4 py-3">Risk Level</th>
                <th className="px-4 py-3">Selected Action</th>
                <th className="px-4 py-3">State</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/50">
              {cases.slice(0, 6).map((c) => (
                <tr key={c.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-3.5 font-mono text-xs text-white">{c.id}</td>
                  <td className="px-4 py-3.5 font-medium text-white">{formatINR(c.amount)}</td>
                  <td className="px-4 py-3.5 text-xs text-slate-300">{c.failureCategory}</td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`px-2 py-0.5 text-xs font-semibold rounded ${
                        c.riskLevel === 'CRITICAL'
                          ? 'bg-rose-950 text-rose-400 border border-rose-800'
                          : c.riskLevel === 'HIGH'
                          ? 'bg-amber-950 text-amber-400 border border-amber-800'
                          : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      }`}
                    >
                      {c.riskLevel}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-semibold text-brand-400">{c.selectedAction || 'ANALYZING'}</td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded ${
                        c.state === 'RECOVERED'
                          ? 'bg-emerald-900/50 text-emerald-300'
                          : c.state === 'STOPPED'
                          ? 'bg-rose-900/50 text-rose-300'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {c.state}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-right">
                    <button
                      onClick={() => navigate(`/recovery/${c.id}`)}
                      className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-white rounded transition-colors"
                    >
                      Inspect →
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
