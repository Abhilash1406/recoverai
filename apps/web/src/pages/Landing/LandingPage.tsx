import React from 'react';
import { Link } from 'react-router-dom';

const PIPELINE_STEPS = [
  'Detect Payment Failure',
  'Diagnose Root Cause',
  'Assess Transaction Risk',
  'Estimate Recovery Probability',
  'Decision Engine (EU)',
  'Policy Safety Gate',
  'Bounded AI Agent',
  'Execute Recovery Action',
  'Measure Revenue Recovered',
  'Audit Trail',
];

const PHASES = [
  {
    number: '1',
    label: 'Foundation',
    status: 'current',
    description: 'Repository, API scaffold, ML structure',
  },
  {
    number: '2',
    label: 'Data + API',
    status: 'upcoming',
    description: 'MongoDB models, REST endpoints, auth',
  },
  {
    number: '3',
    label: 'ML + Razorpay',
    status: 'upcoming',
    description: 'Risk models, recovery probability, sandbox',
  },
  {
    number: '4',
    label: 'Decision Engine',
    status: 'upcoming',
    description: 'Expected utility, policy gate, AI agent',
  },
  {
    number: '5',
    label: 'Full Pipeline',
    status: 'upcoming',
    description: 'End-to-end recovery, audit trail, analytics',
  },
];

/**
 * LandingPage — RecoverAI home page
 *
 * Communicates the product vision and current phase status.
 * No fake analytics, no fabricated statistics.
 */
export function LandingPage(): React.JSX.Element {
  return (
    <div className="min-h-screen bg-surface overflow-x-hidden">
      {/* Hero section */}
      <div className="relative">
        {/* Mesh gradient background */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(77, 99, 248, 0.12), transparent)',
          }}
        />

        {/* Navbar */}
        <header className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-blue-500 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-brand-900/30">
              R
            </div>
            <div>
              <span className="font-bold text-white text-lg tracking-tight">RecoverAI</span>
              <span className="ml-2 text-xs text-slate-500 font-mono">v1.0.0-phase1</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="badge bg-brand-950 text-brand-400 border border-brand-800">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
              Phase 1 — Foundation
            </span>
            <Link
              to="/dashboard"
              className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium transition-colors"
            >
              Open App Shell →
            </Link>
          </div>
        </header>

        {/* Hero content */}
        <div className="relative z-10 px-8 pt-20 pb-16 text-center animate-fade-in">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-brand-800 bg-brand-950/50 text-xs text-brand-400 mb-8">
            <span>Razorpay Buildathon 2026</span>
            <span className="w-px h-3 bg-brand-800" />
            <span className="font-semibold">Track 03 — AI Revenue Recovery</span>
          </div>

          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6 leading-tight">
            Risk-Aware Autonomous{' '}
            <span className="text-gradient">Revenue Recovery</span>
          </h1>

          <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-4">
            RecoverAI treats payment failure recovery as a{' '}
            <span className="text-slate-200 font-medium">constrained decision-optimization problem</span>
            , not a simple retry loop.
          </p>

          <p className="text-sm text-slate-500 max-w-xl mx-auto font-mono bg-surface-card border border-surface-border rounded-lg px-4 py-3 mt-6">
            EU(t, a) = P(recovery | t, a) × value − riskCost − frictionCost − actionCost
          </p>
        </div>
      </div>

      {/* Pipeline visualization */}
      <section className="px-8 py-16 max-w-5xl mx-auto">
        <h2 className="text-sm font-semibold text-brand-400 uppercase tracking-widest mb-8 text-center">
          Recovery Pipeline
        </h2>

        <div className="flex flex-col items-center gap-0">
          {PIPELINE_STEPS.map((step, index) => (
            <div key={step} className="flex flex-col items-center">
              <div className="glass-card px-5 py-3 text-sm text-slate-300 font-medium min-w-64 text-center hover:border-brand-800 transition-colors">
                {step}
              </div>
              {index < PIPELINE_STEPS.length - 1 && (
                <div className="w-px h-5 bg-gradient-to-b from-brand-700 to-transparent" />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Phase roadmap */}
      <section className="px-8 py-16 border-t border-surface-border">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-sm font-semibold text-brand-400 uppercase tracking-widest mb-10 text-center">
            Development Roadmap
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
            {PHASES.map((phase) => (
              <div
                key={phase.number}
                className={`glass-card p-4 rounded-xl transition-all ${
                  phase.status === 'current'
                    ? 'border-brand-700 ring-1 ring-brand-700/50'
                    : 'opacity-60'
                }`}
              >
                <div
                  className={`text-xs font-bold mb-2 ${
                    phase.status === 'current' ? 'text-brand-400' : 'text-slate-500'
                  }`}
                >
                  Phase {phase.number}
                </div>
                <div className="text-sm font-semibold text-white mb-1">{phase.label}</div>
                <div className="text-xs text-slate-500">{phase.description}</div>
                {phase.status === 'current' && (
                  <div className="mt-3 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                    <span className="text-xs text-green-400">In progress</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology stack */}
      <section className="px-8 py-16 border-t border-surface-border bg-surface-card/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-sm font-semibold text-brand-400 uppercase tracking-widest mb-10 text-center">
            Technology Stack
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Frontend', tech: 'React · Vite · TypeScript · Tailwind' },
              { label: 'Backend', tech: 'Node.js · Express · TypeScript' },
              { label: 'ML', tech: 'Python · scikit-learn · XGBoost' },
              { label: 'AI & Payments', tech: 'Gemini · Razorpay (Phase 3+)' },
            ].map((item) => (
              <div key={item.label} className="glass-card p-4">
                <div className="text-xs text-brand-400 font-semibold uppercase tracking-wide mb-2">
                  {item.label}
                </div>
                <div className="text-sm text-slate-300">{item.tech}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-8 py-6 border-t border-surface-border text-center">
        <p className="text-xs text-slate-600">
          RecoverAI — Razorpay Buildathon 2026 · Track 03: AI Revenue Recovery ·{' '}
          <span className="text-slate-500">Phase 1: Engineering Foundation</span>
        </p>
      </footer>
    </div>
  );
}
