import React from 'react';
import { Cloud, CloudRain, Sun, Wind, Thermometer, MoreHorizontal } from 'lucide-react';

export function EnvironmentalWidget() {
  const forecast = [
    { day: 'Mon', temp: '18°', icon: CloudRain, rain: '40%' },
    { day: 'Tue', temp: '19°', icon: Cloud, rain: '10%' },
    { day: 'Wed', temp: '21°', icon: Sun, rain: '0%' },
    { day: 'Thu', temp: '17°', icon: CloudRain, rain: '60%' },
    { day: 'Fri', temp: '18°', icon: Cloud, rain: '20%' },
  ];

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col justify-between h-full border border-cyan-500/20 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/10 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 font-mono text-xs font-bold">[2]</span>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            PAVEMENT WEATHER IMPACT
          </h3>
        </div>
        <MoreHorizontal className="w-4 h-4 text-slate-500 cursor-pointer hover:text-cyan-400" />
      </div>

      {/* Main Temp & Weather Grid */}
      <div className="flex items-center justify-between my-1">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Cloud className="w-8 h-8 animate-pulse" />
          </div>
          <div>
            <div className="text-3xl font-bold font-mono text-slate-100 tracking-tight">18°C</div>
            <div className="text-xs text-cyan-400 font-medium">Overcast / Wet Surface</div>
          </div>
        </div>

        <div className="text-right space-y-1 font-mono text-[11px]">
          <div className="flex items-center justify-end gap-1 text-slate-400">
            <CloudRain className="w-3 h-3 text-cyan-400" />
            <span>Rain Risk: <strong className="text-slate-200">10%</strong></span>
          </div>
          <div className="flex items-center justify-end gap-1 text-slate-400">
            <Wind className="w-3 h-3 text-cyan-400" />
            <span>Wind: <strong className="text-slate-200">14 km/h NE</strong></span>
          </div>
          <div className="flex items-center justify-end gap-1 text-slate-400">
            <Thermometer className="w-3 h-3 text-amber-400" />
            <span>Asphalt Temp: <strong className="text-amber-400">22.4°C</strong></span>
          </div>
        </div>
      </div>

      {/* 5-Day Mini Forecast Strip */}
      <div className="grid grid-cols-5 gap-1.5 mt-3 pt-3 border-t border-cyan-500/10">
        {forecast.map((f, i) => {
          const Icon = f.icon;
          return (
            <div key={i} className="bg-[#080d19]/90 p-2 rounded border border-cyan-500/10 flex flex-col items-center justify-between text-center">
              <span className="text-[10px] font-mono text-slate-400 uppercase">{f.day}</span>
              <Icon className="w-4 h-4 text-cyan-400 my-1" />
              <span className="text-xs font-mono font-bold text-slate-200">{f.temp}</span>
              <span className="text-[9px] font-mono text-slate-500">{f.rain}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
