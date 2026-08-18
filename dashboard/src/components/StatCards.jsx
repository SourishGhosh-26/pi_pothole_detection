import React from 'react';
import { AlertTriangle, Clock, CheckCircle2, ShieldCheck, Flame } from 'lucide-react';

export function StatCards({ stats }) {
  const cards = [
    {
      title: 'Total Detections',
      value: stats.total || 0,
      subtext: `${stats.high_severity || 0} High Severity`,
      icon: AlertTriangle,
      color: 'text-amber-400',
      bg: 'from-amber-500/10 to-orange-500/5',
      border: 'border-amber-500/20',
    },
    {
      title: 'Needs Verification',
      value: stats.needs_verification || 0,
      subtext: 'Pending Review',
      icon: Clock,
      color: 'text-rose-400',
      bg: 'from-rose-500/10 to-pink-500/5',
      border: 'border-rose-500/20',
    },
    {
      title: 'Verified',
      value: stats.verified || 0,
      subtext: 'Confirmed Road Hazards',
      icon: CheckCircle2,
      color: 'text-sky-400',
      bg: 'from-sky-500/10 to-blue-500/5',
      border: 'border-sky-500/20',
    },
    {
      title: 'Fixed / Repaired',
      value: stats.fixed || 0,
      subtext: 'Resolved Work Orders',
      icon: ShieldCheck,
      color: 'text-emerald-400',
      bg: 'from-emerald-500/10 to-teal-500/5',
      border: 'border-emerald-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`glass-card p-5 rounded-2xl border ${card.border} bg-gradient-to-br ${card.bg} transition-all duration-300 hover:translate-y-[-2px] shadow-lg`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {card.title}
                </p>
                <h3 className="text-3xl font-black tracking-tight text-white mt-1">
                  {card.value}
                </h3>
                <p className="text-xs text-slate-400 mt-1 font-medium">
                  {card.subtext}
                </p>
              </div>
              <div className={`p-3 rounded-xl bg-slate-900/60 border border-white/5 ${card.color}`}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
