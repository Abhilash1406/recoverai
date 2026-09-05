import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';

interface NavItem {
  path: string;
  label: string;
  icon: string;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: '⬡', badge: 'Live' },
  { path: '/recovery', label: 'Recovery Cases', icon: '◈', badge: 'AI' },
  { path: '/transactions', label: 'Transactions', icon: '⟳' },
  { path: '/decisions', label: 'Decision Log', icon: '◆' },
  { path: '/analytics', label: 'Analytics', icon: '↗' },
  { path: '/audit', label: 'Audit Trail', icon: '≡' },
  { path: '/experiments', label: 'Experiments', icon: '🧪' },
];

export function Sidebar(): React.JSX.Element {
  const [gatewayMode, setGatewayMode] = useState<'MOCK_DEMO' | 'RAZORPAY_SANDBOX'>('MOCK_DEMO');

  useEffect(() => {
    fetch('/api/v1/health')
      .then((res) => res.json())
      .then((data) => {
        if (data?.gatewayMode === 'RAZORPAY_SANDBOX') {
          setGatewayMode('RAZORPAY_SANDBOX');
        }
      })
      .catch(() => {});
  }, []);

  return (
    <aside className="w-60 flex-shrink-0 border-r border-surface-border flex flex-col bg-slate-950">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-surface-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-blue-500 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-brand-500/20">
            R
          </div>
          <span className="font-semibold text-white text-sm">RecoverAI</span>
        </div>
        <p className="text-xs text-slate-500 mt-1 ml-9">Revenue Recovery Engine</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`
            }
          >
            <span className="text-sm leading-none">{item.icon}</span>
            <span className="flex-1">{item.label}</span>
            {item.badge && (
              <span className="text-[10px] bg-brand-500/20 text-brand-300 px-1.5 py-0.5 rounded font-mono">
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Mode Indicator Footer */}
      <div className="px-4 py-4 border-t border-surface-border space-y-2">
        <div className={`glass-card p-3 border ${gatewayMode === 'RAZORPAY_SANDBOX' ? 'border-emerald-500/30 bg-emerald-950/20' : 'border-amber-500/30 bg-amber-950/20'}`}>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full animate-pulse ${gatewayMode === 'RAZORPAY_SANDBOX' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
            <p className={`text-[11px] font-bold uppercase tracking-wider ${gatewayMode === 'RAZORPAY_SANDBOX' ? 'text-emerald-400' : 'text-amber-400'}`}>
              {gatewayMode === 'RAZORPAY_SANDBOX' ? '💳 RAZORPAY SANDBOX' : '⚡ MOCK DEMO MODE'}
            </p>
          </div>
          <p className="text-[10px] text-slate-400 mt-1 leading-tight">
            {gatewayMode === 'RAZORPAY_SANDBOX' ? 'Live Razorpay Test API Integration' : 'Simulated Gateway (No keys required)'}
          </p>
        </div>
        <div className="glass-card p-2.5 border border-purple-500/30 bg-purple-950/20">
          <div className="flex items-center gap-2">
            <span className="text-purple-400 text-xs">✦</span>
            <p className="text-[10px] font-semibold text-purple-300">Gemini Explanation Agent</p>
          </div>
          <p className="text-[9px] text-slate-400 mt-0.5">Deterministic Decision Authority</p>
        </div>
      </div>
    </aside>
  );
}
