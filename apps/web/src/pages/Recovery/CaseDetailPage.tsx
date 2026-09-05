import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchCaseDetail, analyzeCase, executeCaseAction } from '../../services/api';

export function CaseDetailPage(): React.JSX.Element {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [data, setData] = useState<any>(null);

  const loadCase = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await fetchCaseDetail(id);
      if (res.success) {
        setData(res.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCase();
  }, [id]);

  const handleAnalyze = async () => {
    if (!id) return;
    setExecuting(true);
    await analyzeCase(id);
    await loadCase();
    setExecuting(false);
  };

  const handleExecute = async () => {
    if (!id) return;
    setExecuting(true);
    await executeCaseAction(id);
    await loadCase();
    setExecuting(false);
  };

  const formatINR = (paise: number) => {
    return `₹${((paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400">
        Loading Recovery Case Details...
      </div>
    );
  }

  if (!data || !data.case) {
    return (
      <div className="p-8 text-center text-rose-400">
        Recovery Case {id} not found.{' '}
        <button onClick={() => navigate('/dashboard')} className="underline">
          Return to Dashboard
        </button>
      </div>
    );
  }

  const { case: recCase, decision, auditEvents } = data;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Back & Header */}
      <div className="flex items-center justify-between border-b border-surface-border pb-6">
        <div>
          <button
            onClick={() => navigate('/recovery')}
            className="text-xs font-medium text-slate-400 hover:text-white mb-2 flex items-center gap-1"
          >
            ← Back to Recovery Cases
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white font-mono">{recCase.id}</h1>
            <span
              className={`px-2.5 py-1 text-xs font-semibold rounded ${
                recCase.state === 'RECOVERED'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  : recCase.state === 'STOPPED'
                  ? 'bg-rose-950 text-rose-400 border border-rose-800'
                  : 'bg-brand-950 text-brand-400 border border-brand-800'
              }`}
            >
              {recCase.state}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleAnalyze}
            disabled={executing}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-medium text-xs rounded transition-colors"
          >
            Re-Analyze Case
          </button>
          <button
            onClick={handleExecute}
            disabled={executing || recCase.state === 'RECOVERED' || recCase.state === 'STOPPED'}
            className="px-5 py-2 bg-gradient-to-r from-brand-500 to-blue-600 hover:from-brand-600 hover:to-blue-700 text-white font-medium text-xs rounded shadow-lg shadow-brand-500/20 transition-all disabled:opacity-50"
          >
            {executing ? 'Executing...' : `Execute Action (${recCase.selectedAction || 'RETRY'})`}
          </button>
        </div>
      </div>

      {/* Transaction & Risk Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="glass-card p-5">
          <p className="text-xs text-slate-400 font-medium uppercase">Transaction Amount</p>
          <p className="text-2xl font-bold text-white mt-1">{formatINR(recCase.amount)}</p>
          <p className="text-xs text-slate-400 mt-2">
            Failure Category: <span className="text-amber-400 font-semibold">{recCase.failureCategory}</span>
          </p>
        </div>

        <div className="glass-card p-5">
          <p className="text-xs text-slate-400 font-medium uppercase">Risk Assessment</p>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-2xl font-bold text-white">{(recCase.riskScore * 100).toFixed(0)}%</p>
            <span
              className={`px-2 py-0.5 text-xs font-semibold rounded ${
                recCase.riskLevel === 'CRITICAL'
                  ? 'bg-rose-950 text-rose-400 border border-rose-800'
                  : recCase.riskLevel === 'HIGH'
                  ? 'bg-amber-950 text-amber-400 border border-amber-800'
                  : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
              }`}
            >
              {recCase.riskLevel}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Customer Opt-Out:{' '}
            <span className={recCase.customerOptedOut ? 'text-rose-400 font-bold' : 'text-emerald-400 font-semibold'}>
              {recCase.customerOptedOut ? 'YES (COMMUNICATIONS BLOCKED)' : 'NO'}
            </span>
          </p>
        </div>

        <div className="glass-card p-5">
          <p className="text-xs text-slate-400 font-medium uppercase">Selected Action</p>
          <p className="text-2xl font-bold text-brand-400 mt-1">{recCase.selectedAction || 'ANALYZING'}</p>
          <p className="text-xs text-slate-400 mt-2">
            Attempt Count: <span className="text-white font-semibold">{recCase.attemptCount}</span>
          </p>
        </div>
      </div>

      {/* Decision Explainability & Expected Utility Table */}
      {decision && (
        <div className="glass-card p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-surface-border pb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Decision Engine & Counterfactual Action Ranking</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Expected Utility = P(recovery) × Amount − Risk Cost − Friction Cost − Action Cost (Policy threshold: P ≥ 60%)
              </p>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-emerald-950 border border-emerald-800 px-2.5 py-1 rounded">
              Status: {decision.status}
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/80 text-xs text-slate-400 uppercase border-b border-surface-border">
                <tr>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Predicted P(recovery)</th>
                  <th className="px-4 py-3">Expected Utility (₹)</th>
                  <th className="px-4 py-3">Policy Gate</th>
                  <th className="px-4 py-3">Status / Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/50">
                {decision.candidateScores?.map((score: any) => (
                  <tr
                    key={score.action}
                    className={
                      score.action === recCase.selectedAction
                        ? 'bg-brand-950/40 font-medium border-l-4 border-l-brand-500'
                        : 'hover:bg-slate-800/40'
                    }
                  >
                    <td className="px-4 py-3.5 font-semibold text-white">{score.action}</td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-brand-500 h-full rounded-full"
                            style={{ width: `${(score.recoveryProbability * 100).toFixed(0)}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-slate-300">
                          {(score.recoveryProbability * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-white">
                      ₹{(score.expectedUtility / 100).toFixed(2)}
                    </td>
                    <td className="px-4 py-3.5">
                      <span
                        className={`px-2 py-0.5 text-xs font-semibold rounded ${
                          score.allowed
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : 'bg-rose-950 text-rose-400 border border-rose-800'
                        }`}
                      >
                        {score.allowed ? 'ALLOWED' : 'REJECTED'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400">
                      {score.allowed ? 'Optimal safe action' : score.rejectionReason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Gemini AI Rationale & Explanation Card */}
      <div className="glass-card p-6 border-l-4 border-l-purple-500">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 rounded bg-purple-500 flex items-center justify-center text-white text-xs font-bold">
            ✦
          </div>
          <h2 className="text-base font-semibold text-white">AI Explanation of Decision (Gemini)</h2>
          <span className="text-xs text-purple-400 bg-purple-950 border border-purple-800 px-2 py-0.5 rounded font-mono ml-auto">
            Zero Decision Authority (Explanation Only)
          </span>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed">
          {recCase.explanation || 'Generated explanation of the deterministic RecoverAI decision.'}
        </p>
      </div>

      {/* Immutable Audit Trail Timeline */}
      <div className="glass-card p-6">
        <h2 className="text-base font-semibold text-white mb-4">Immutable Audit Trail Timeline</h2>
        <div className="space-y-4">
          {auditEvents?.map((evt: any) => (
            <div key={evt.id} className="flex gap-4 items-start border-l-2 border-slate-800 pl-4 py-1">
              <div className="w-3 h-3 rounded-full bg-brand-500 mt-1 flex-shrink-0" />
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-bold text-white font-mono">{evt.eventType}</span>
                  <span className="text-xs text-slate-500 font-mono">Actor: {evt.actor}</span>
                  <span className="text-xs text-slate-500 ml-auto">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1">{evt.reason}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
