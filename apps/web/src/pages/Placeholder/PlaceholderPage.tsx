import React from 'react';
interface PlaceholderPageProps {
  title: string;
  phase: string;
}

/**
 * PlaceholderPage — shown for routes not yet implemented
 *
 * Each page in the app shell uses this until its Phase is implemented.
 */
export function PlaceholderPage({ title, phase }: PlaceholderPageProps): React.JSX.Element {
  return (
    <div className="h-full flex items-center justify-center p-8">
      <div className="text-center animate-fade-in">
        <div className="w-16 h-16 rounded-2xl bg-brand-950 border border-brand-800 flex items-center justify-center mx-auto mb-6">
          <span className="text-2xl font-bold text-brand-500">P{phase}</span>
        </div>
        <h1 className="text-2xl font-bold text-white mb-3">{title}</h1>
        <p className="text-slate-400 text-sm mb-6 max-w-sm">
          This page will be implemented in <span className="text-brand-400 font-semibold">Phase {phase}</span> of RecoverAI.
        </p>
        <div className="glass-card inline-block px-4 py-2">
          <p className="text-xs text-slate-500 font-mono">Phase 1 — Foundation only</p>
        </div>
      </div>
    </div>
  );
}
