import React, { useState } from 'react';
import { Search, Filter, Eye, MapPin, AlertCircle, CheckCircle2, Clock } from 'lucide-react';

export function HistoryTable({ detections, onSelectDetection }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');

  const filteredDetections = detections.filter((det) => {
    const matchesSearch =
      det.id.toString().includes(searchTerm) ||
      det.lat.toString().includes(searchTerm) ||
      det.lon.toString().includes(searchTerm);

    const matchesStatus = statusFilter === 'all' || det.status === statusFilter;
    const matchesSeverity = severityFilter === 'all' || det.severity === severityFilter;

    return matchesSearch && matchesStatus && matchesSeverity;
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'reported':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Clock className="w-3 h-3" /> Reported
          </span>
        );
      case 'verified':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertCircle className="w-3 h-3" /> Verified
          </span>
        );
      case 'fixed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> Fixed
          </span>
        );
      default:
        return status;
    }
  };

  const getSeverityBadge = (severity) => {
    switch (severity) {
      case 'high':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'medium':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      default:
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    }
  };

  return (
    <div className="glass-panel rounded-3xl border border-white/10 p-6 shadow-2xl mt-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div>
          <h2 className="text-lg font-bold text-white">Detection History Log</h2>
          <p className="text-xs text-slate-400">All registered potholes with spatial GPS tags & confidence scores</p>
        </div>

        {/* Search & Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          {/* Search bar */}
          <div className="relative flex-1 sm:w-48">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search ID/GPS..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="reported">Reported</option>
            <option value="verified">Verified</option>
            <option value="fixed">Fixed</option>
          </select>

          {/* Severity filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
          >
            <option value="all">All Severities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-white/5 bg-slate-900/40">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-900/80 uppercase font-semibold text-[10px] tracking-wider text-slate-400 border-b border-white/5">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">GPS Location</th>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">YOLO Conf.</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filteredDetections.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-8 text-center text-slate-500">
                  No pothole detections match the current filters.
                </td>
              </tr>
            ) : (
              filteredDetections.map((det) => (
                <tr
                  key={det.id}
                  onClick={() => onSelectDetection(det)}
                  className="hover:bg-indigo-500/5 transition-colors cursor-pointer group"
                >
                  <td className="px-4 py-3 font-bold text-white font-mono">#{det.id}</td>
                  <td className="px-4 py-3 font-mono text-slate-300">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-indigo-400 inline" />
                      {det.lat.toFixed(5)}, {det.lon.toFixed(5)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-mono">
                    {new Date(det.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2.5 py-0.5 rounded-full font-bold uppercase text-[10px] tracking-wider border ${getSeverityBadge(det.severity)}`}>
                      {det.severity}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-semibold text-slate-200">
                    {(det.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-3">{getStatusBadge(det.status)}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectDetection(det);
                      }}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white transition-all shadow"
                      title="View Details"
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
