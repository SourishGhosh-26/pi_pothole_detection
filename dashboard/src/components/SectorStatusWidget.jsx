import React from 'react';
import { Route, MoreHorizontal } from 'lucide-react';

export function SectorStatusWidget({ detections = [] }) {
  const highCount = detections.filter(d => d.severity === 'high' && d.status !== 'fixed').length;
  const mediumCount = detections.filter(d => d.severity === 'medium' && d.status !== 'fixed').length;

  const sectors = [
    {
      id: 'SEC-A',
      name: 'Sector A: Downtown Core',
      status: highCount > 0 ? 'ATTENTION' : 'OPTIMAL',
      detail: highCount > 0 ? `${highCount} Critical Pothole(s)` : 'All roads clear',
      color: highCount > 0 ? 'text-rose-400 border-rose-500/30 bg-rose-500/10' : 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
    },
    {
      id: 'SEC-B',
      name: 'Sector B: Metro Expressway',
      status: mediumCount > 0 ? 'DISPATCHED' : 'OPTIMAL',
      detail: mediumCount > 0 ? 'Patching Crew En-Route' : 'Flow 98%',
      color: mediumCount > 0 ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' : 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
    },
    {
      id: 'SEC-C',
      name: 'Sector C: North Arterial',
      status: 'OPTIMAL',
      detail: 'Pothole Patrol Complete',
      color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
    }
  ];

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col justify-between h-full border border-cyan-500/20 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/10 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 font-mono text-xs font-bold">[4]</span>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Route className="w-3.5 h-3.5 text-cyan-400" />
            ROAD SECTORS & REPAIR SQUADS
          </h3>
        </div>
        <MoreHorizontal className="w-4 h-4 text-slate-500 cursor-pointer hover:text-cyan-400" />
      </div>

      {/* Mini Transit Map Overlay Graphic */}
      <div className="relative h-16 w-full mb-3 rounded bg-[#070b16] border border-cyan-500/10 overflow-hidden p-2 flex items-center justify-between">
        <svg className="absolute inset-0 w-full h-full text-cyan-500/20 stroke-current" viewBox="0 0 200 60">
          <line x1="10" y1="15" x2="190" y2="15" strokeWidth="2" strokeDasharray="4,4" />
          <line x1="30" y1="45" x2="170" y2="45" strokeWidth="2" />
          <line x1="40" y1="10" x2="140" y2="50" strokeWidth="3" className="text-emerald-500/50" />
          <circle cx="40" cy="10" r="4" fill="#06b6d4" />
          <circle cx="100" cy="30" r="5" fill="#f43f5e" />
          <circle cx="140" cy="50" r="4" fill="#10b981" />
        </svg>

        <div className="relative z-10 font-mono text-[10px] text-cyan-400 bg-[#070b16]/80 px-2 py-1 rounded border border-cyan-500/20">
          SURFACE FLOW: <strong className="text-emerald-400">94% NORMAL</strong>
        </div>

        <div className="relative z-10 font-mono text-[10px] text-slate-400 bg-[#070b16]/80 px-2 py-1 rounded border border-cyan-500/20">
          ACTIVE UNITS: <strong className="text-slate-200">12 PATROL CAMS</strong>
        </div>
      </div>

      {/* Sector Status List */}
      <div className="space-y-2 flex-1 flex flex-col justify-around">
        {sectors.map((sec) => (
          <div key={sec.id} className="bg-[#080d19]/90 p-2 rounded border border-cyan-500/10 flex items-center justify-between">
            <div>
              <div className="text-xs font-medium text-slate-200">{sec.name}</div>
              <div className="text-[10px] font-mono text-slate-400">{sec.detail}</div>
            </div>

            <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border uppercase shrink-0 ${sec.color}`}>
              {sec.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
