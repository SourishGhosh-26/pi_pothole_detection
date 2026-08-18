import React from 'react';
import { Camera, AlertTriangle, MoreHorizontal, Maximize2 } from 'lucide-react';
import { API_BASE } from '../utils/api';

export function LiveCameraGridWidget({ detections = [], liveFrame, onSelectDetection, onOpenDashCam }) {
  const cameraFeeds = [
    {
      id: 'CAM-01',
      title: 'CAM-01: FRONT DASH CAM',
      isDashCam: true,
      detection: detections[0],
      placeholder: 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=400&q=80',
    },
    {
      id: 'CAM-02',
      title: 'Metro Highway Sector',
      detection: detections[1],
      placeholder: 'https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=400&q=80',
    },
    {
      id: 'CAM-03',
      title: 'Financial Dist Hub',
      detection: detections[2],
      placeholder: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=400&q=80',
    },
    {
      id: 'CAM-04',
      title: 'Expressway Flyover',
      detection: detections[3],
      placeholder: 'https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&w=400&q=80',
    },
  ];

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col justify-between h-full border border-cyan-500/20 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cyan-500/10 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 font-mono text-xs font-bold">[3]</span>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Camera className="w-3.5 h-3.5 text-cyan-400" />
            LIVE POTHOLE DETECTION CAMERAS
          </h3>
        </div>
        <MoreHorizontal className="w-4 h-4 text-slate-500 cursor-pointer hover:text-cyan-400" />
      </div>

      {/* 2x2 Feed Grid */}
      <div className="grid grid-cols-2 gap-2 flex-1">
        {cameraFeeds.map((cam, index) => {
          const hasDetection = !!cam.detection;
          const isLiveFeedStream = index === 0 && liveFrame;
          const imageUrl = isLiveFeedStream
            ? (liveFrame.startsWith('data:image') ? liveFrame : `data:image/jpeg;base64,${liveFrame}`)
            : (hasDetection && cam.detection.image_path
                ? `${API_BASE}/api/detections/${cam.detection.id}/image`
                : cam.placeholder);

          const handleClick = () => {
            if (cam.isDashCam && onOpenDashCam) {
              onOpenDashCam();
            } else if (hasDetection && onSelectDetection) {
              onSelectDetection(cam.detection);
            }
          };

          return (
            <div 
              key={cam.id} 
              onClick={handleClick}
              className="relative rounded-lg overflow-hidden border border-cyan-500/20 bg-[#070b16] group cursor-pointer aspect-video flex flex-col justify-between p-2 shadow-inner"
            >
              {/* Image */}
              <img 
                src={imageUrl} 
                alt={cam.title}
                onError={(e) => { e.target.src = cam.placeholder; }}
                className="absolute inset-0 w-full h-full object-cover opacity-70 group-hover:opacity-90 transition-opacity group-hover:scale-105 duration-300"
              />

              {/* Overlay Gradient */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#070b16] via-transparent to-black/60 pointer-events-none" />

              {/* Top Row Badges */}
              <div className="relative z-10 flex items-center justify-between">
                <span className="inline-flex items-center gap-1 bg-rose-500/20 text-rose-400 border border-rose-500/40 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded backdrop-blur">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                  {cam.isDashCam ? '[DASH CAM LIVE]' : '[LIVE]'}
                </span>

                {hasDetection && (
                  <span className="bg-rose-500/90 text-white text-[9px] font-mono font-bold px-1.5 py-0.5 rounded shadow flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    POTHOLE DETECTED
                  </span>
                )}
              </div>

              {/* Bottom Title Bar */}
              <div className="relative z-10 flex items-center justify-between text-[11px] font-mono text-slate-200">
                <span className="truncate drop-shadow">{cam.title}</span>
                <Maximize2 className="w-3.5 h-3.5 text-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-1" />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
