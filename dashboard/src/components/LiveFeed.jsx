import React, { useState, useEffect, useRef } from 'react';
import { Camera, Radio, AlertTriangle, ShieldCheck, Video, VideoOff } from 'lucide-react';

export function LiveFeed({ liveFrame, frameTimestamp, hasDetection }) {
  const [fps, setFps] = useState(0);
  const frameCountRef = useRef(0);
  const lastFpsCalcRef = useRef(Date.now());

  // Calculate live FPS
  useEffect(() => {
    if (!liveFrame) return;

    frameCountRef.current += 1;
    const now = Date.now();
    const elapsed = (now - lastFpsCalcRef.current) / 1000;

    if (elapsed >= 1.0) {
      setFps(Math.round(frameCountRef.current / elapsed));
      frameCountRef.current = 0;
      lastFpsCalcRef.current = now;
    }
  }, [liveFrame]);

  return (
    <div className="relative w-full h-[520px] rounded-3xl overflow-hidden glass-panel border border-white/10 shadow-2xl flex flex-col bg-[#0F172A]">
      {/* Header Overlay */}
      <div className="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
        {/* Stream Status Badge */}
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl glass-panel text-xs font-semibold text-slate-200 border border-white/10 shadow-lg pointer-events-auto">
          <span className={`w-2.5 h-2.5 rounded-full ${liveFrame ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
          <span className="flex items-center gap-1.5">
            <Camera className="w-3.5 h-3.5 text-indigo-400" />
            {liveFrame ? 'Live Camera Feed' : 'Waiting for Feed'}
          </span>
        </div>

        {/* Live FPS & Detections Status */}
        {liveFrame && (
          <div className="flex items-center gap-2 pointer-events-auto">
            {hasDetection && (
              <span className="px-3 py-1 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-bold uppercase tracking-wider animate-pulse flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> Pothole Flagged
              </span>
            )}
            <span className="px-3 py-1 rounded-xl glass-panel text-xs font-mono font-bold text-indigo-300 border border-white/10 shadow-md">
              {fps > 0 ? `${fps} FPS` : 'STREAMING'}
            </span>
          </div>
        )}
      </div>

      {/* Main Video Stream Container */}
      <div className="relative flex-1 w-full h-full flex items-center justify-center bg-slate-950 overflow-hidden">
        {liveFrame ? (
          <img
            src={liveFrame}
            alt="Pi Zero 2 W Live Camera Feed"
            className="w-full h-full object-contain bg-black transition-all duration-75"
          />
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center text-slate-500 shadow-xl">
              <VideoOff className="w-8 h-8 animate-pulse" />
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-200">Waiting for Camera Stream...</h4>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Connect the Raspberry Pi Zero 2 W streamer to <code className="text-indigo-400 font-mono">/ws/ingest</code> or click <strong className="text-indigo-300">Simulate Detection</strong> above to test.
              </p>
            </div>
          </div>
        )}

        {/* Bottom Timestamp Bar */}
        {liveFrame && frameTimestamp && (
          <div className="absolute bottom-4 left-4 z-20 px-3 py-1 rounded-xl glass-panel text-[11px] font-mono text-slate-300 border border-white/10">
            TIME: {new Date(frameTimestamp * 1000).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
}
