import React, { useState } from 'react';
import { X, MapPin, Calendar, CheckCircle, ShieldAlert, Cpu, Check, Loader2 } from 'lucide-react';
import { API_BASE, updateDetectionStatus } from '../utils/api';

export function DetectionModal({ detection, onClose, onStatusUpdated }) {
  const [currentStatus, setCurrentStatus] = useState(detection.status);
  const [updating, setUpdating] = useState(false);

  if (!detection) return null;

  const handleStatusChange = async (e) => {
    const newStatus = e.target.value;
    setUpdating(true);
    try {
      await updateDetectionStatus(detection.id, newStatus);
      setCurrentStatus(newStatus);
      onStatusUpdated(detection.id, newStatus);
    } catch (err) {
      alert('Failed to update status: ' + err.message);
    } finally {
      setUpdating(false);
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'high':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      case 'medium':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    }
  };

  const imageUrl = detection.image_path.startsWith('http')
    ? detection.image_path
    : `${API_BASE}${detection.image_path}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div className="glass-panel relative w-full max-w-lg rounded-3xl overflow-hidden border border-white/10 shadow-2xl bg-[#111827]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center font-black text-sm">
              #{detection.id}
            </span>
            <div>
              <h3 className="font-bold text-lg text-white">Pothole Detection Detail</h3>
              <p className="text-xs text-slate-400">Session ID: {detection.session_id || 'default'}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Snapshot Image */}
          <div className="relative rounded-2xl overflow-hidden border border-white/10 bg-slate-900 aspect-video shadow-lg">
            <img
              src={imageUrl}
              alt={`Pothole #${detection.id}`}
              className="w-full h-full object-cover"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = 'https://via.placeholder.com/640x480/1F2937/FFFFFF?text=Snapshot+Image+Unavailable';
              }}
            />
            <div className="absolute top-3 right-3 flex items-center gap-2 px-3 py-1 rounded-full glass-panel text-xs font-bold text-white shadow-md">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span>YOLO Conf: {(detection.confidence * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="glass-card p-3 rounded-xl border border-white/5 space-y-1">
              <span className="text-slate-400 font-medium flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-indigo-400" /> GPS Location
              </span>
              <p className="text-sm font-bold text-white font-mono">
                {detection.lat.toFixed(5)}, {detection.lon.toFixed(5)}
              </p>
            </div>

            <div className="glass-card p-3 rounded-xl border border-white/5 space-y-1">
              <span className="text-slate-400 font-medium flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-indigo-400" /> Timestamp
              </span>
              <p className="text-sm font-bold text-white font-mono">
                {new Date(detection.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </p>
            </div>
          </div>

          {/* Severity & Status controls */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Severity Level</span>
              <span className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider border ${getSeverityBadge(detection.severity)}`}>
                {detection.severity}
              </span>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center justify-between">
                <span>Update Status</span>
                {updating && <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />}
              </label>
              <div className="relative">
                <select
                  value={currentStatus}
                  onChange={handleStatusChange}
                  disabled={updating}
                  className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-indigo-500/30 text-white font-semibold text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all appearance-none cursor-pointer"
                >
                  <option value="reported">🔴 Reported (Needs Verification)</option>
                  <option value="verified">🟡 Verified Hazard</option>
                  <option value="fixed">🟢 Fixed / Repaired</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/10 bg-slate-900/50 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
