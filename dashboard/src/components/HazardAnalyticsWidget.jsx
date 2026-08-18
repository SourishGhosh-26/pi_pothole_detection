import React from 'react';
import { MoreHorizontal } from 'lucide-react';

export function HazardAnalyticsWidget({ detections = [] }) {
  const total = detections.length;
  const reported = detections.filter(d => d.status === 'reported' || !d.status).length;
  const verified = detections.filter(d => d.status === 'verified').length;
  const fixed = detections.filter(d => d.status === 'fixed').length;

  const verifiedPercent = total ? Math.round((verified / total) * 100) : 0;
  const fixedPercent = total ? Math.round((fixed / total) * 100) : 0;

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col justify-between h-full border border-cyan-500/20 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/10 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 font-mono text-xs font-bold">[1]</span>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            POTHOLE HAZARD ANALYTICS
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded font-semibold uppercase">
            STATUS: ACTIVE
          </span>
          <MoreHorizontal className="w-4 h-4 text-slate-500 cursor-pointer hover:text-cyan-400" />
        </div>
      </div>

      {/* Main Stat Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div className="bg-[#080d19]/80 p-3 rounded-lg border border-cyan-500/10">
          <span className="text-[10px] text-slate-400 font-mono block uppercase">Total Detected</span>
          <div className="text-2xl font-bold font-mono text-cyan-400 tracking-tight mt-0.5">
            {total} <span className="text-xs font-normal text-slate-500 font-sans">potholes</span>
          </div>
        </div>

        <div className="bg-[#080d19]/80 p-3 rounded-lg border border-emerald-500/10">
          <span className="text-[10px] text-slate-400 font-mono block uppercase">Repairs Completed</span>
          <div className="text-2xl font-bold font-mono text-emerald-400 tracking-tight mt-0.5">
            {fixed} <span className="text-xs font-normal text-slate-500 font-sans">({fixedPercent}%)</span>
          </div>
        </div>
      </div>

      {/* Synthetic Futuristic Wave / Trend Area Graphic */}
      <div className="relative h-16 w-full my-1 rounded bg-[#070b16] border border-cyan-500/10 overflow-hidden flex items-end px-2 pt-2">
        <div className="absolute top-1 left-2 text-[9px] font-mono text-slate-500">24H DETECTION WAVE</div>
        <svg className="w-full h-12 text-cyan-500/30" viewBox="0 0 200 40" preserveAspectRatio="none">
          <defs>
            <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="amberGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          <path d="M0,35 Q30,15 60,25 T120,10 T180,28 L200,35 L200,40 L0,40 Z" fill="url(#cyanGrad)" />
          <path d="M0,35 Q30,15 60,25 T120,10 T180,28 L200,35" fill="none" stroke="#06b6d4" strokeWidth="2" />
          
          <path d="M0,38 Q40,25 80,30 T140,20 T200,32 L200,40 L0,40 Z" fill="url(#amberGrad)" />
          <path d="M0,38 Q40,25 80,30 T140,20 T200,32" fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="3,3" />
        </svg>
      </div>

      {/* Progress Bars */}
      <div className="space-y-2 mt-2">
        <div>
          <div className="flex justify-between text-[10px] font-mono mb-1">
            <span className="text-slate-400">UNVERIFIED (REPORTED)</span>
            <span className="text-amber-400">{reported} ({total ? Math.round((reported/total)*100) : 0}%)</span>
          </div>
          <div className="h-1.5 w-full bg-[#0a101f] rounded-full overflow-hidden border border-amber-500/20">
            <div 
              className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 rounded-full transition-all duration-500"
              style={{ width: `${total ? (reported/total)*100 : 0}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-[10px] font-mono mb-1">
            <span className="text-slate-400">VERIFIED (PENDING FIX)</span>
            <span className="text-cyan-400">{verified} ({verifiedPercent}%)</span>
          </div>
          <div className="h-1.5 w-full bg-[#0a101f] rounded-full overflow-hidden border border-cyan-500/20">
            <div 
              className="h-full bg-gradient-to-r from-cyan-500 to-sky-400 rounded-full transition-all duration-500"
              style={{ width: `${verifiedPercent}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
