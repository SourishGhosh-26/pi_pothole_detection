import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

export function LiveMap({ detections = [], selectedDetection, onSelectDetection, currentGps }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersGroupRef = useRef(null);
  const userGpsMarkerRef = useRef(null);

  const activeCount = detections.filter(d => d.status !== 'fixed').length;
  const criticalCount = detections.filter(d => d.severity === 'high' && d.status !== 'fixed').length;

  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const initialLat = currentGps ? currentGps.lat : 19.0760;
      const initialLon = currentGps ? currentGps.lon : 72.8777;

      const map = L.map(mapContainerRef.current, {
        center: [initialLat, initialLon],
        zoom: 15,
        zoomControl: false,
        attributionControl: false
      });

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: ['a', 'b', 'c', 'd'],
      }).addTo(map);

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      markersGroupRef.current = L.layerGroup().addTo(map);
      mapInstanceRef.current = map;

      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 250);
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current || !currentGps) return;
    const { lat, lon } = currentGps;
    const map = mapInstanceRef.current;

    const userIcon = L.divIcon({
      className: 'custom-user-gps-icon',
      html: `
        <div class="relative flex items-center justify-center w-8 h-8">
          <div class="absolute w-8 h-8 rounded-full bg-cyan-500/30 animate-ping"></div>
          <div class="relative w-4 h-4 rounded-full bg-cyan-400 border-2 border-slate-900 shadow-lg shadow-cyan-500/50"></div>
        </div>
      `,
      iconSize: [32, 32],
      iconAnchor: [16, 16]
    });

    if (!userGpsMarkerRef.current) {
      userGpsMarkerRef.current = L.marker([lat, lon], { icon: userIcon }).addTo(map);
      map.setView([lat, lon], map.getZoom());
    } else {
      userGpsMarkerRef.current.setLatLng([lat, lon]);
    }
  }, [currentGps]);

  useEffect(() => {
    if (!mapInstanceRef.current || !markersGroupRef.current) return;
    const markersGroup = markersGroupRef.current;
    markersGroup.clearLayers();

    detections.forEach((det) => {
      let colorClass = 'bg-amber-500 border-amber-300 shadow-amber-500/50';
      let ringColor = 'bg-amber-500/30';
      let isHigh = false;

      if (det.severity === 'high') {
        colorClass = 'bg-rose-500 border-rose-300 shadow-rose-500/50';
        ringColor = 'bg-rose-500/40';
        isHigh = true;
      } else if (det.severity === 'low') {
        colorClass = 'bg-emerald-500 border-emerald-300 shadow-emerald-500/50';
        ringColor = 'bg-emerald-500/30';
      }

      const isSelected = selectedDetection && selectedDetection.id === det.id;

      const markerHtml = `
        <div class="relative group cursor-pointer transition-transform duration-300 hover:scale-125 ${isSelected ? 'scale-125 z-50' : ''}">
          <div class="absolute -inset-1 rounded-full ${ringColor} ${isHigh ? 'animate-ping' : ''}"></div>
          <div class="relative w-7 h-7 rounded-full ${colorClass} border-2 shadow-xl flex items-center justify-center text-white text-[10px] font-black">
            ${det.id}
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        className: 'custom-pothole-marker',
        html: markerHtml,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const marker = L.marker([det.lat, det.lon], { icon: customIcon });

      marker.on('click', () => {
        if (onSelectDetection) onSelectDetection(det);
      });

      markersGroup.addLayer(marker);
    });
  }, [detections, selectedDetection, onSelectDetection]);

  useEffect(() => {
    if (selectedDetection && mapInstanceRef.current) {
      mapInstanceRef.current.panTo([selectedDetection.lat, selectedDetection.lon], {
        animate: true,
        duration: 0.8
      });
    }
  }, [selectedDetection]);

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden glass-panel border border-cyan-500/30 shadow-[0_0_30px_rgba(6,182,212,0.15)] flex flex-col">
      {/* Top Header Overlay Bar */}
      <div className="z-20 bg-[#070b16]/90 border-b border-cyan-500/20 backdrop-blur px-4 py-2 flex items-center justify-between font-mono text-xs text-slate-200">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 font-bold">[0] LIVE POTHOLE & GIS MAP</span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">GPS TELEMETRY ACTIVE</span>
        </div>

        <div className="flex items-center gap-4 text-[11px]">
          <div>Potholes Active: <strong className="text-cyan-400">{activeCount}</strong></div>
          <div>Critical Potholes: <strong className="text-rose-400">{criticalCount}</strong></div>
        </div>
      </div>

      {/* Map Viewport Container */}
      <div className="relative flex-1 w-full h-full min-h-[400px]">
        <div 
          ref={mapContainerRef} 
          style={{ height: '100%', width: '100%', minHeight: '400px', zIndex: 1 }} 
          className="w-full h-full" 
        />

        {/* Bottom Legend Overlay Bar inside Map */}
        <div className="absolute bottom-3 left-3 z-[400] bg-[#070b16]/90 border border-cyan-500/20 backdrop-blur rounded-lg px-3 py-1.5 flex items-center gap-4 text-[10px] font-mono shadow-lg">
          <div className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]" />
            <span>Low Hazard</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_6px_#f59e0b]" />
            <span>Moderate</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-400 shadow-[0_0_6px_#f43f5e]" />
            <span>Critical Pothole</span>
          </div>
        </div>
      </div>
    </div>
  );
}
