import React from 'react';
import { LayoutDashboard, Map, Table, MapPinned, Settings, ShieldCheck, Camera } from 'lucide-react';

export function Sidebar({ currentView, onViewChange }) {
  const navItems = [
    { id: 'live', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'dashcam', label: 'Dash Cam Stream', icon: Camera },
    { id: 'traffic', label: 'Pothole Map', icon: Map },
    { id: 'historical', label: 'Historical Logs', icon: Table },
    { id: 'replay', label: 'Route Replay', icon: MapPinned },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="w-60 bg-[#070b16]/80 border-r border-cyan-500/20 backdrop-blur-xl flex flex-col h-full z-20 shadow-[5px_0_25px_rgba(0,0,0,0.5)] select-none">
      {/* Brand Logo Header */}
      <div className="p-5 border-b border-cyan-500/10 flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.3)]">
          <ShieldCheck className="w-5 h-5 text-cyan-400" />
        </div>
        <div>
          <h1 className="text-sm font-bold text-slate-100 tracking-wider font-mono">PATCHSENSE</h1>
          <span className="text-[9px] font-mono text-cyan-400/70 uppercase tracking-widest block">POTHOLE OS v2.4</span>
        </div>
      </div>
      
      {/* Navigation List */}
      <nav className="flex-1 p-3 space-y-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all duration-200 group relative ${
                isActive 
                  ? "bg-gradient-to-r from-cyan-500/20 to-cyan-500/5 text-cyan-300 border border-cyan-500/30 shadow-[0_0_15px_rgba(6,182,212,0.15)] font-semibold" 
                  : "text-slate-400 hover:bg-cyan-500/5 hover:text-slate-200 border border-transparent"
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-cyan-400 rounded-r shadow-[0_0_8px_#06b6d4]" />
              )}
              <Icon className={`w-4 h-4 transition-colors ${isActive ? "text-cyan-400" : "text-slate-500 group-hover:text-cyan-400"}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer System Health */}
      <div className="p-4 border-t border-cyan-500/10 bg-[#050810]/60">
        <div className="flex items-center justify-between text-[10px] font-mono mb-1.5">
          <span className="text-slate-500">SYSTEM HEALTH</span>
          <span className="text-emerald-400 font-bold">100%</span>
        </div>
        <div className="h-1 w-full bg-slate-900 rounded-full overflow-hidden border border-emerald-500/20">
          <div className="h-full bg-emerald-400 rounded-full w-full shadow-[0_0_8px_#10b981]" />
        </div>
      </div>
    </div>
  );
}
