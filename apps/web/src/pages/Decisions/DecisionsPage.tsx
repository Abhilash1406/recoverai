import React, { useEffect, useState } from 'react';
import { fetchDecisions } from '../../services/api';

export function DecisionsPage(): React.JSX.Element {
  const [loading, setLoading] = useState(true);
  const [decisions, setDecisions] = useState<any[]>([]);

  useEffect(() => {
    fetchDecisions()
      .then((res) => {
        if (res.success) setDecisions(res.data);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="border-b border-surface-border pb-6">
        <h1 className="text-2xl font-bold text-white">Decision Engine Log</h1>
        <p className="text-sm text-slate-400 mt-1">Expected Utility calculations and Policy Gate evaluations</p>
      </div>

      <div className="glass-card p-6">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs text-slate-400 uppercase border-b border-surface-border">
              <tr>
                <th className="px-4 py-3">Decision ID</th>
                <th className="px-4 py-3">Transaction ID</th>
                <th className="px-4 py-3">Recommended Action</th>
                <th className="px-4 py-3">Expected Utility</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/50">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Loading decisions...
                  </td>
                </tr>
              ) : (
                decisions.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3.5 font-mono text-xs text-white">{d.id}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{d.transactionId}</td>
                    <td className="px-4 py-3.5 font-semibold text-brand-400">{d.recommendedAction}</td>
                    <td className="px-4 py-3.5 font-mono text-emerald-400">₹{(d.expectedUtility || 0).toFixed(2)}</td>
                    <td className="px-4 py-3.5">
                      <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                        {d.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-300 max-w-md truncate">{d.rationale}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
