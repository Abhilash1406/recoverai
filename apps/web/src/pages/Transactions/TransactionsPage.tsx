import React, { useEffect, useState } from 'react';
import { fetchTransactions } from '../../services/api';

export function TransactionsPage(): React.JSX.Element {
  const [loading, setLoading] = useState(true);
  const [txns, setTxns] = useState<any[]>([]);

  useEffect(() => {
    fetchTransactions()
      .then((res) => {
        if (res.success) setTxns(res.data);
      })
      .finally(() => setLoading(false));
  }, []);

  const formatINR = (paise: number) => `₹${((paise || 0) / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="border-b border-surface-border pb-6">
        <h1 className="text-2xl font-bold text-white">Failed Transactions Log</h1>
        <p className="text-sm text-slate-400 mt-1">Monitored transactions ingested into RecoverAI pipeline</p>
      </div>

      <div className="glass-card p-6">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs text-slate-400 uppercase border-b border-surface-border">
              <tr>
                <th className="px-4 py-3">Transaction ID</th>
                <th className="px-4 py-3">Customer ID</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Failure Category</th>
                <th className="px-4 py-3">Failure Code</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Created At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/50">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    Loading transactions...
                  </td>
                </tr>
              ) : (
                txns.map((t) => (
                  <tr key={t.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3.5 font-mono text-xs text-white">{t.id}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{t.customerId}</td>
                    <td className="px-4 py-3.5 font-medium text-white">{formatINR(t.amount)}</td>
                    <td className="px-4 py-3.5 text-xs text-slate-300">{t.failureCategory}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{t.failureCode || 'N/A'}</td>
                    <td className="px-4 py-3.5">
                      <span className="px-2 py-0.5 text-xs font-semibold rounded bg-rose-950 text-rose-400 border border-rose-800">
                        {t.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-slate-400">
                      {new Date(t.createdAt).toLocaleTimeString()}
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
