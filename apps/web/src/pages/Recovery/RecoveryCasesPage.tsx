import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchRecoveryCases } from '../../services/api';

export function RecoveryCasesPage(): React.JSX.Element {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState<any[]>([]);

  useEffect(() => {
    fetchRecoveryCases()
      .then((res) => {
        if (res.success) setCases(res.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const formatINR = (paise: number) => `₹${((paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center justify-between border-b border-surface-border pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Recovery Cases</h1>
          <p className="text-sm text-slate-400 mt-1">Manage and inspect autonomous recovery cases</p>
        </div>
      </div>

      <div className="glass-card p-6">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs text-slate-400 uppercase border-b border-surface-border">
              <tr>
                <th className="px-4 py-3">Case ID</th>
                <th className="px-4 py-3">Transaction ID</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Failure Category</th>
                <th className="px-4 py-3">Risk Level</th>
                <th className="px-4 py-3">Selected Action</th>
                <th className="px-4 py-3">State</th>
                <th className="px-4 py-3 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/50">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                    Loading cases...
                  </td>
                </tr>
              ) : (
                cases.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3.5 font-mono text-xs text-white">{c.id}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{c.transactionId}</td>
                    <td className="px-4 py-3.5 font-medium text-white">{formatINR(c.amount)}</td>
                    <td className="px-4 py-3.5 text-xs text-slate-300">{c.failureCategory}</td>
                    <td className="px-4 py-3.5">
                      <span className="px-2 py-0.5 text-xs font-semibold rounded bg-slate-800 text-brand-400">
                        {c.riskLevel}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-semibold text-brand-400">{c.selectedAction || 'ANALYZING'}</td>
                    <td className="px-4 py-3.5">
                      <span className="px-2 py-0.5 text-xs font-medium rounded bg-slate-800 text-slate-300">
                        {c.state}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <button
                        onClick={() => navigate(`/recovery/${c.id}`)}
                        className="px-3 py-1 bg-brand-500 hover:bg-brand-600 text-xs font-medium text-white rounded transition-colors"
                      >
                        Inspect →
                      </button>
                    </td>
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
