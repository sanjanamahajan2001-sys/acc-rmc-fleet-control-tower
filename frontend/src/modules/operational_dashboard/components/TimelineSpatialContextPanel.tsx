import React from 'react';
import { SpatialContext } from '../api/timelineReplayApi';
import { MapPin, Navigation, ShieldCheck, AlertTriangle, HelpCircle } from 'lucide-react';

interface TimelineSpatialContextPanelProps {
  spatialContext?: SpatialContext | null;
  plantName?: string;
  customerName?: string;
}

export const TimelineSpatialContextPanel: React.FC<TimelineSpatialContextPanelProps> = ({
  spatialContext,
  plantName = 'ACC Plant',
  customerName = 'Customer Site',
}) => {
  if (!spatialContext) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-center text-slate-500">
        <HelpCircle className="w-8 h-8 mx-auto text-slate-600 mb-2" />
        <p className="text-sm font-semibold text-slate-300">NO SPATIAL DATA AVAILABLE</p>
        <p className="text-xs text-slate-500 mt-1">
          Spatial context is missing from backend DTO.
        </p>
      </div>
    );
  }

  const {
    spatial_mode,
    plant_latitude,
    plant_longitude,
    site_latitude,
    site_longitude,
    trajectory_points = [],
    has_gps_breadcrumbs = false,
  } = spatialContext;

  const isGpsMode =
    spatial_mode === 'GPS_TRAJECTORY' &&
    has_gps_breadcrumbs &&
    trajectory_points.length > 0;

  const isLocationMode =
    spatial_mode === 'LOCATION_CONTEXT_ONLY' ||
    (spatial_mode === 'GPS_TRAJECTORY' && (!has_gps_breadcrumbs || trajectory_points.length === 0));

  const isNoDataMode =
    spatial_mode === 'NO_SPATIAL_DATA' ||
    (plant_latitude === null &&
      plant_longitude === null &&
      site_latitude === null &&
      site_longitude === null &&
      trajectory_points.length === 0);

  const hasPlantCoords = plant_latitude !== null && plant_longitude !== null;
  const hasSiteCoords = site_latitude !== null && site_longitude !== null;

  // Calculate SVG ViewBox limits for clean rendering
  const renderSvgMap = () => {
    let lats: number[] = [];
    let lons: number[] = [];

    if (hasPlantCoords) {
      lats.push(plant_latitude!);
      lons.push(plant_longitude!);
    }
    if (hasSiteCoords) {
      lats.push(site_latitude!);
      lons.push(site_longitude!);
    }
    if (isGpsMode && trajectory_points.length > 0) {
      trajectory_points.forEach((tp: { latitude: number | null; longitude: number | null }) => {
        if (tp.latitude !== null && tp.longitude !== null) {
          lats.push(tp.latitude);
          lons.push(tp.longitude);
        }
      });
    }

    if (lats.length === 0 || lons.length === 0) {
      return null;
    }

    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);

    const width = 600;
    const height = 180;

    const toSvgX = (lon: number) => {
      if (maxLon === minLon) return width / 2;
      return ((lon - minLon) / (maxLon - minLon)) * (width - 80) + 40;
    };

    const toSvgY = (lat: number) => {
      if (maxLat === minLat) return height / 2;
      return height - (((lat - minLat) / (maxLat - minLat)) * (height - 80) + 40);
    };

    const plantSvg = hasPlantCoords ? { x: toSvgX(plant_longitude!), y: toSvgY(plant_latitude!) } : null;
    const siteSvg = hasSiteCoords ? { x: toSvgX(site_longitude!), y: toSvgY(site_latitude!) } : null;

    let breadcrumbPath = '';
    if (isGpsMode) {
      breadcrumbPath = trajectory_points
        .filter((tp: { latitude: number | null; longitude: number | null }) => tp.latitude !== null && tp.longitude !== null)
        .map((tp: { latitude: number | null; longitude: number | null }, idx: number) => {
          const sx = toSvgX(tp.longitude!);
          const sy = toSvgY(tp.latitude!);
          return `${idx === 0 ? 'M' : 'L'} ${sx} ${sy}`;
        })
        .join(' ');
    }

    return (
      <div className="relative w-full h-[220px] bg-slate-950/80 rounded-lg border border-slate-800/80 overflow-hidden flex items-center justify-center">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 opacity-10 pointer-events-none"
          style={{
            backgroundImage: `radial-gradient(#4f46e5 1px, transparent 1px)`,
            backgroundSize: '16px 16px',
          }}
        />

        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="z-10">
          {/* LOCATION CONTEXT LINE (Never labeled as vehicle route) */}
          {isLocationMode && plantSvg && siteSvg && (
            <line
              x1={plantSvg.x}
              y1={plantSvg.y}
              x2={siteSvg.x}
              y2={siteSvg.y}
              stroke="#06b6d4"
              strokeWidth="2"
              strokeDasharray="4 4"
              className="opacity-70"
            />
          )}

          {/* GPS BREADCRUMB TRAJECTORY POLYLINE (Actual backend points only) */}
          {isGpsMode && breadcrumbPath && (
            <path
              d={breadcrumbPath}
              fill="none"
              stroke="#10b981"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="drop-shadow-md"
            />
          )}

          {/* Plant Location Marker */}
          {plantSvg && (
            <g transform={`translate(${plantSvg.x}, ${plantSvg.y})`}>
              <circle r="12" fill="#4f46e5" fillOpacity="0.2" />
              <circle r="6" fill="#6366f1" stroke="#ffffff" strokeWidth="1.5" />
              <text y="-12" textAnchor="middle" className="fill-indigo-300 text-[10px] font-bold font-sans">
                {plantName} (Plant)
              </text>
            </g>
          )}

          {/* Site Location Marker */}
          {siteSvg && (
            <g transform={`translate(${siteSvg.x}, ${siteSvg.y})`}>
              <circle r="12" fill="#06b6d4" fillOpacity="0.2" />
              <circle r="6" fill="#22d3ee" stroke="#ffffff" strokeWidth="1.5" />
              <text y="-12" textAnchor="middle" className="fill-cyan-300 text-[10px] font-bold font-sans">
                {customerName} (Site)
              </text>
            </g>
          )}
        </svg>

        {/* Dynamic Map Legend Overlay */}
        <div className="absolute bottom-2 right-2 bg-slate-900/90 border border-slate-800 rounded px-2.5 py-1 text-[10px] space-y-0.5 text-slate-300 z-20">
          {hasPlantCoords && (
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              <span>Plant Location</span>
            </div>
          )}
          {hasSiteCoords && (
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              <span>Site / Unloading Location</span>
            </div>
          )}
          {isLocationMode && hasPlantCoords && hasSiteCoords && (
            <div className="flex items-center gap-1.5 text-cyan-300">
              <span className="w-3 border-t border-dashed border-cyan-400" />
              <span>Location Context Line</span>
              <span className="text-[9px] text-slate-400">(Not Vehicle Route)</span>
            </div>
          )}
          {isGpsMode && (
            <div className="flex items-center gap-1.5 text-emerald-300">
              <span className="w-3 border-t-2 border-emerald-400" />
              <span>GPS Trajectory Path ({trajectory_points.length} pts)</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-md space-y-3">
      {/* Header & Authority Status Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
        <div className="flex items-center space-x-2">
          <MapPin className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Spatial Context &amp; Location Capability
          </h3>
        </div>

        {/* Explicit Authority Badge */}
        <div>
          {isGpsMode && !isNoDataMode && (
            <span className="inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
              <ShieldCheck className="w-3 h-3 mr-1" />
              GPS TRAJECTORY AVAILABLE ({trajectory_points.length} BREADCRUMBS)
            </span>
          )}

          {isLocationMode && !isNoDataMode && (
            <span className="inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
              <Navigation className="w-3 h-3 mr-1" />
              AUTHORITATIVE TIMELINE (LOCATION CONTEXT ONLY - NO GPS BREADCRUMBS)
            </span>
          )}

          {isNoDataMode && (
            <span className="inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
              <AlertTriangle className="w-3 h-3 mr-1" />
              NO SPATIAL DATA AVAILABLE
            </span>
          )}
        </div>
      </div>

      {/* Main Panel Content */}
      {isNoDataMode ? (
        <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-8 text-center text-slate-500 space-y-2">
          <HelpCircle className="w-8 h-8 mx-auto text-slate-600 mb-1" />
          <p className="text-sm font-semibold text-slate-300">NO SPATIAL DATA AVAILABLE</p>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Neither GPS breadcrumbs nor valid Plant/Site location coordinates exist for this dispatch record in PostgreSQL.
          </p>
        </div>
      ) : (
        <>
          {renderSvgMap()}

          {/* Coordinate Detail Breakdown Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
            <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                Plant Location Coordinates ({plantName})
              </span>
              {hasPlantCoords ? (
                <span className="font-mono text-slate-200 font-semibold">
                  Lat: {plant_latitude!.toFixed(6)}, Lon: {plant_longitude!.toFixed(6)}
                </span>
              ) : (
                <span className="text-slate-500 italic">Coordinates Unavailable</span>
              )}
            </div>

            <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                Site / Unloading Location Coordinates ({customerName})
              </span>
              {hasSiteCoords ? (
                <span className="font-mono text-slate-200 font-semibold">
                  Lat: {site_latitude!.toFixed(6)}, Lon: {site_longitude!.toFixed(6)}
                </span>
              ) : (
                <span className="text-slate-500 italic">Coordinates Unavailable</span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
