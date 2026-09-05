import React from 'react';

export function ExperimentsPage(): React.JSX.Element {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="border-b border-surface-border pb-6">
        <h1 className="text-2xl font-bold text-white">Multi-Seed Experiments Benchmark</h1>
        <p className="text-sm text-slate-400 mt-1">Scientific simulation results across seeds [42, 123, 456, 789, 1001]</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="glass-card p-6 border-l-4 border-l-brand-500">
          <h2 className="text-base font-semibold text-white mb-2">Seed=42 Baseline Benchmark (n=1,000)</h2>
          <div className="space-y-2 text-xs text-slate-300 font-mono">
            <div className="flex justify-between p-2 bg-slate-900/60 rounded">
              <span>AlwaysRetry:</span> <span>Recovery: 33.26% | Net: ₹8.98M</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-900/60 rounded">
              <span>AlwaysPaymentLink:</span> <span>Recovery: 30.45% | Net: ₹7.06M</span>
            </div>
            <div className="flex justify-between p-2 bg-slate-900/60 rounded">
              <span>RuleBased:</span> <span>Recovery: 55.51% | Net: ₹12.24M</span>
            </div>
            <div className="flex justify-between p-2 bg-brand-950/80 rounded border border-brand-800">
              <span className="font-bold text-brand-400">RecoverAI (ML-Powered):</span>{' '}
              <span className="font-bold text-brand-300">Recovery: 34.13% | Net: ₹10.24M</span>
            </div>
          </div>
        </div>

        <div className="glass-card p-6 border-l-4 border-l-emerald-500">
          <h2 className="text-base font-semibold text-white mb-2">Scientific Validation Metrics</h2>
          <div className="space-y-2 text-xs text-slate-300">
            <div className="flex justify-between border-b border-slate-800 pb-1.5">
              <span>Recovery Model ROC-AUC:</span> <span className="font-mono text-emerald-400 font-bold">0.8521</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-1.5">
              <span>Grouped Split ROC-AUC:</span> <span className="font-mono text-emerald-400 font-bold">0.8710</span>
            </div>
            <div className="flex justify-between border-b border-slate-800 pb-1.5">
              <span>Expected Calibration Error (ECE):</span> <span className="font-mono text-emerald-400 font-bold">0.0521</span>
            </div>
            <div className="flex justify-between">
              <span>Safety Policy Gate Violations:</span> <span className="font-mono text-emerald-400 font-bold">0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
