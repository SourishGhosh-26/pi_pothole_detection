import React from 'react';
import { Activity, Radio, Navigation, Play, MapPin, RefreshCw } from 'lucide-react';

export function Header({ liveConnected, gpsActive, currentGps, onTriggerSim, onRefresh }) {
  return (
    <header className="glass-panel sticky top-0 z-40 px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4 shadow-xl border-b border-white/10">
      {/* Brand Title */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-violet-600 to-amber-500 p-0.5 shadow-lg shadow-indigo-500/20">
          <div className="w-full h-full bg-[#0B0F17] rounded-[10px] flex items-center justify-center">
            <Activity className="w-5 h-5 text-indigo-400 animate-pulse" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">
              PATCHSENSE
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              v1.0 Demo
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">Real-time Pothole Detection & Road-Mapping System</p>
        </div>
      </div>

      {/* Status Badges & Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Live Server WS Status */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border ${
          liveConnected 
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
            : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
        }`}>
          <Radio className={`w-3.5 h-3.5 ${liveConnected ? 'animate-pulse' : ''}`} />
          <span>{liveConnected ? 'Server Connected' : 'Disconnected'}</span>
        </div>

        {/* GPS Tracker Status */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border ${
          gpsActive 
            ? 'bg-sky-500/10 text-sky-400 border-sky-500/20' 
            : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
        }`}>
          <Navigation className={`w-3.5 h-3.5 ${gpsActive ? 'animate-spin-slow text-sky-400' : ''}`} />
          <span>
            {gpsActive && currentGps
              ? `GPS: ${currentGps.lat.toFixed(4)}, ${currentGps.lon.toFixed(4)}`
              : 'GPS Seeking...'}
          </span>
        </div>

        {/* Refresh button */}
        <button
          onClick={onRefresh}
          className="p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 transition-colors border border-white/5"
          title="Refresh Data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        {/* Simulation Demo Trigger Button */}
        <button
          onClick={onTriggerSim}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all hover:scale-105 active:scale-95"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Simulate Detection</span>
        </button>
      </div>
    </header>
  );
}
