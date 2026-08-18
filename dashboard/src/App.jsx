import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { LiveMap } from './components/LiveMap';
import { HazardAnalyticsWidget } from './components/HazardAnalyticsWidget';
import { EnvironmentalWidget } from './components/EnvironmentalWidget';
import { LiveCameraGridWidget } from './components/LiveCameraGridWidget';
import { SectorStatusWidget } from './components/SectorStatusWidget';
import { HistoryTable } from './components/HistoryTable';
import { LiveFeed } from './components/LiveFeed';
import { DetectionModal } from './components/DetectionModal';
import { AlertTicker } from './components/AlertTicker';
import { fetchDetections, fetchStats, triggerSimulatedDetection, API_BASE } from './utils/api';
import { ShieldCheck, Bell, User, Clock, Loader2, Play } from 'lucide-react';

export default function App() {
  const [currentView, setCurrentView] = useState('live');
  const [detections, setDetections] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    needs_verification: 0,
    verified: 0,
    fixed: 0,
    high_severity: 0,
    medium_severity: 0,
    low_severity: 0,
  });
  const [selectedDetection, setSelectedDetection] = useState(null);
  const [currentGps, setCurrentGps] = useState(null);
  const [liveConnected, setLiveConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Live Camera Stream State
  const [liveFrame, setLiveFrame] = useState(null);

  const gpsWsRef = useRef(null);
  const liveWsRef = useRef(null);

  // Clock tick timer
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // 1. Initial Data Fetch
  const loadData = async () => {
    try {
      const [dets, st] = await Promise.all([fetchDetections(), fetchStats()]);
      setDetections(dets);
      setStats(st);
    } catch (err) {
      console.error('Failed to load initial data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // 2. Browser Geolocation Stream
  useEffect(() => {
    if (!('geolocation' in navigator)) return;

    const host = window.location.hostname || 'localhost';
    const gpsWsUrl = `ws://${host}:8000/ws/gps`;
    
    let ws = null;
    try {
      ws = new WebSocket(gpsWsUrl);
      gpsWsRef.current = ws;
    } catch (e) {
      console.error('GPS WS init failed:', e);
    }

    const handleGpsSuccess = (position) => {
      const { latitude, longitude } = position.coords;
      const coords = { lat: latitude, lon: longitude, timestamp: Date.now() / 1000 };
      setCurrentGps(coords);

      if (gpsWsRef.current && gpsWsRef.current.readyState === WebSocket.OPEN) {
        gpsWsRef.current.send(JSON.stringify(coords));
      }
    };

    navigator.geolocation.getCurrentPosition(handleGpsSuccess, null, { enableHighAccuracy: false, timeout: 5000 });
    const watchId = navigator.geolocation.watchPosition(handleGpsSuccess, null, { enableHighAccuracy: true, timeout: 10000 });

    return () => {
      navigator.geolocation.clearWatch(watchId);
      if (gpsWsRef.current) gpsWsRef.current.close();
    };
  }, []);

  // 3. Connect Live Broadcast WebSocket (`/ws/live`)
  useEffect(() => {
    const host = window.location.hostname || 'localhost';
    const liveWsUrl = `ws://${host}:8000/ws/live`;
    let ws = null;
    let reconnectTimeout = null;

    const connectLiveWs = () => {
      ws = new WebSocket(liveWsUrl);
      liveWsRef.current = ws;

      ws.onopen = () => setLiveConnected(true);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'LIVE_FRAME') {
            setLiveFrame(data.image);
          } else if ((data.type === 'NEW_DETECTION' || data.type === 'new_detection') && (data.detection || data.data)) {
            const newDet = data.detection || data.data;
            setDetections((prev) => {
              if (prev.find(d => d.id === newDet.id)) return prev;
              return [newDet, ...prev];
            });
            fetchStats().then(setStats).catch(() => {});
          } else if (data.type === 'STATUS_UPDATE') {
            const { detection_id, status } = data;
            setDetections((prev) =>
              prev.map((d) => (d.id === detection_id ? { ...d, status } : d))
            );
            fetchStats().then(setStats).catch(() => {});
          }
        } catch (err) {
          console.error('Live WS parse error:', err);
        }
      };

      ws.onclose = () => {
        setLiveConnected(false);
        reconnectTimeout = setTimeout(connectLiveWs, 3000);
      };
    };

    connectLiveWs();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) ws.close();
    };
  }, []);

  const handleTriggerSim = async () => {
    try {
      await triggerSimulatedDetection();
      loadData();
    } catch (err) {
      alert('Failed to trigger simulation: ' + err.message);
    }
  };

  const handleStatusUpdated = (id, newStatus) => {
    setDetections((prev) =>
      prev.map((d) => (d.id === id ? { ...d, status: newStatus } : d))
    );
    fetchStats().then(setStats).catch(() => {});
  };

  const highCount = detections.filter(d => d.severity === 'high' && d.status !== 'fixed').length;

  return (
    <div className="flex flex-col h-screen bg-[#05070e] text-slate-100 overflow-hidden font-sans select-none">
      {/* Top Smart City Command Header Bar */}
      <header className="h-14 bg-[#070b16]/90 border-b border-cyan-500/20 backdrop-blur-xl px-5 flex items-center justify-between shrink-0 z-30 shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
        {/* Left Title */}
        <div className="flex items-center gap-3 font-mono">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <ShieldCheck className="w-5 h-5 shadow-[0_0_10px_#06b6d4]" />
          </div>
          <div className="flex items-center gap-2 text-xs font-bold tracking-wider">
            <span className="text-slate-100">PATCHSENSE POTHOLE MONITORING COMMAND</span>
            <span className="text-cyan-500/50">|</span>
            <span className="text-cyan-400 font-semibold uppercase">LIVE ANALYTICS [CENTRAL]</span>
          </div>
        </div>

        {/* Right Status Controls & User */}
        <div className="flex items-center gap-4 font-mono text-xs">
          {/* Trigger Simulation Button */}
          <button
            onClick={handleTriggerSim}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-[11px] font-bold transition-all shadow-[0_0_10px_rgba(6,182,212,0.2)]"
          >
            <Play className="w-3 h-3 fill-current" />
            <span>TRIGGER SIMULATION</span>
          </button>

          {/* WebSocket Status Indicator Pill */}
          <div className={`flex items-center gap-2 px-2.5 py-1 rounded-full border text-[11px] font-bold ${
            liveConnected 
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
              : 'bg-rose-500/10 text-rose-400 border-rose-500/30 shadow-[0_0_10px_rgba(244,63,94,0.2)]'
          }`}>
            <span className={`w-2 h-2 rounded-full ${liveConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            <span>{liveConnected ? 'LIVE FEED: CONNECTED' : 'DISCONNECTED'}</span>
          </div>

          {/* Live UTC Clock */}
          <div className="flex items-center gap-2 text-slate-300 bg-[#080d19] px-3 py-1 rounded-lg border border-cyan-500/15">
            <Clock className="w-3.5 h-3.5 text-cyan-400" />
            <span>{currentTime.toLocaleTimeString()} UTC+1</span>
            <span className="text-slate-500 text-[10px]">{currentTime.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })}</span>
          </div>

          {/* Notification Bell Badge */}
          <div className="relative cursor-pointer group">
            <div className="p-2 rounded-lg bg-[#080d19] border border-cyan-500/15 text-slate-300 group-hover:text-cyan-400 transition-colors">
              <Bell className="w-4 h-4" />
            </div>
            {highCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-rose-500 text-white rounded-full text-[9px] font-bold flex items-center justify-center border border-slate-900 animate-bounce">
                {highCount}
              </span>
            )}
          </div>

          {/* User Profile Pill */}
          <div className="flex items-center gap-2.5 bg-[#080d19] border border-cyan-500/20 px-3 py-1 rounded-lg">
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-slate-900 font-bold text-xs">
              <User className="w-3.5 h-3.5 text-white" />
            </div>
            <div>
              <span className="block text-slate-200 text-[11px] font-bold leading-tight">Alex R.</span>
              <span className="block text-[9px] text-cyan-400 uppercase leading-none">ADMIN</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden relative">
        <Sidebar currentView={currentView} onViewChange={setCurrentView} />

        <main className="flex-1 flex flex-col relative overflow-hidden bg-[#05070e] p-3 gap-3">
          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center space-y-4">
              <Loader2 className="w-10 h-10 text-cyan-400 animate-spin" />
              <div className="text-cyan-400 font-mono text-xs font-bold tracking-widest uppercase animate-pulse">
                INITIALIZING COMMAND OS PIPELINE...
              </div>
            </div>
          ) : (
            <>
              {(currentView === 'live' || currentView === 'traffic') && (
                <div className="flex-1 grid grid-cols-12 gap-3 h-full overflow-hidden">
                  {/* Left Column: GIS Live Map (7/12 width) */}
                  <div className="col-span-7 h-full relative">
                    <LiveMap 
                      detections={detections} 
                      selectedDetection={selectedDetection}
                      onSelectDetection={setSelectedDetection}
                      currentGps={currentGps}
                    />
                  </div>

                  {/* Right Column: 2x2 Grid of Command Widgets (5/12 width) */}
                  <div className="col-span-5 grid grid-cols-2 grid-rows-2 gap-3 h-full overflow-hidden">
                    <HazardAnalyticsWidget detections={detections} />
                    <EnvironmentalWidget />
                    <LiveCameraGridWidget 
                      detections={detections} 
                      liveFrame={liveFrame}
                      onSelectDetection={setSelectedDetection} 
                      onOpenDashCam={() => setCurrentView('dashcam')}
                    />
                    <SectorStatusWidget detections={detections} />
                  </div>
                </div>
              )}

              {currentView === 'dashcam' && (
                <div className="flex-1 rounded-xl overflow-hidden glass-panel border border-cyan-500/20 p-3 h-full">
                  <LiveFeed liveFrame={liveFrame} />
                </div>
              )}

              {currentView === 'historical' && (
                <div className="flex-1 rounded-xl overflow-hidden glass-panel border border-cyan-500/20 p-4">
                  <HistoryTable 
                    detections={detections} 
                    onSelectDetection={setSelectedDetection} 
                  />
                </div>
              )}

              {/* Detection Detail Modal */}
              {selectedDetection && (
                <DetectionModal 
                  detection={selectedDetection} 
                  onClose={() => setSelectedDetection(null)} 
                  onStatusUpdated={handleStatusUpdated}
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Bottom Live Alert Marquee Ticker */}
      <AlertTicker detections={detections} />
    </div>
  );
}
