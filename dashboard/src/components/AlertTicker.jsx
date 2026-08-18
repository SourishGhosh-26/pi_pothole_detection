import React from 'react';
import { AlertTriangle, ShieldCheck, Activity, Radio } from 'lucide-react';

export function AlertTicker({ detections = [] }) {
  const recentDetections = detections.slice(0, 8);

  return (
    <div className="h-9 bg-[#070b14]/90 border-t border-cyan-500/20 backdrop-blur flex items-center overflow-hidden px-4 text-xs font-mono select-none z-30 shadow-[0_-5px_15px_rgba(0,0,0,0.5)]">
      {/* Label Badge */}
      <div className="flex items-center gap-2 pr-4 border-r border-cyan-500/20 text-cyan-400 font-semibold whitespace-nowrap bg-[#070b14] z-10 py-1">
        <Radio className="w-3.5 h-3.5 animate-pulse text-rose-500" />
        <span className="tracking-widest uppercase text-[10px]">LIVE POTHOLE TICKER</span>
      </div>

      {/* Scrolling marquee */}
      <div className="flex-1 overflow-hidden relative flex items-center">
        <div className="animate-marquee flex items-center space-x-8">
          {recentDetections.length === 0 ? (
            <div className="flex items-center gap-2 text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>SYSTEM ALL CLEAR — MONITORING ROAD SECTORS IN REALTIME</span>
            </div>
          ) : (
            recentDetections.concat(recentDetections).map((item, idx) => (
              <div key={`${item.id}-${idx}`} className="flex items-center gap-2 shrink-0">
                <span className="text-cyan-500/60">[{new Date(item.timestamp * 1000 || item.created_at || Date.now()).toLocaleTimeString()}]</span>
                {item.severity === 'high' ? (
                  <span className="inline-flex items-center gap-1 text-rose-400 font-semibold bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                    <AlertTriangle className="w-3 h-3 text-rose-400" />
                    CRITICAL POTHOLE #{item.id}
                  </span>
                ) : item.severity === 'medium' ? (
                  <span className="inline-flex items-center gap-1 text-amber-400 font-semibold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                    <Activity className="w-3 h-3 text-amber-400" />
                    MODERATE POTHOLE #{item.id}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    <ShieldCheck className="w-3 h-3 text-emerald-400" />
                    MINOR POTHOLE #{item.id}
                  </span>
                )}
                <span className="text-slate-300">
                  @ {item.lat?.toFixed(4)}, {item.lon?.toFixed(4)}
                </span>
                <span className="text-slate-500 text-[11px]">
                  (Status: <span className="uppercase text-slate-400">{item.status || 'REPORTED'}</span>)
                </span>
                <span className="text-cyan-500/30 font-bold">•</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
