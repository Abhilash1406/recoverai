import React, { useEffect, useState } from 'react';
import { fetchAuditLogs } from '../../services/api';

export function AuditPage(): React.JSX.Element {
  const [loading, setLoading] = useState(true);
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    fetchAuditLogs()
      .then((res) => {
        if (res.success) setEvents(res.data);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="border-b border-surface-border pb-6">
        <h1 className="text-2xl font-bold text-white">Immutable Audit Trail</h1>
        <p className="text-sm text-slate-400 mt-1">Complete verifiable decision and recovery execution history</p>
      </div>

      <div className="glass-card p-6">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-900/80 text-xs text-slate-400 uppercase border-b border-surface-border">
              <tr>
                <th className="px-4 py-3">Event ID</th>
                <th className="px-4 py-3">Case ID</th>
                <th className="px-4 py-3">Event Type</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Reason / Details</th>
                <th className="px-4 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/50">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                    Loading audit trail...
                  </td>
                </tr>
              ) : (
                events.map((evt) => (
                  <tr key={evt.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{evt.id}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-white">{evt.caseId}</td>
                    <td className="px-4 py-3.5 font-mono text-xs font-bold text-brand-400">{evt.eventType}</td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-300">{evt.actor}</td>
                    <td className="px-4 py-3.5 text-xs text-slate-300 max-w-md truncate">{evt.reason}</td>
                    <td className="px-4 py-3.5 text-xs text-slate-400 font-mono">
                      {new Date(evt.timestamp).toLocaleTimeString()}
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
