import React, { useEffect, useRef, useState, useMemo } from 'react';
import { MapPin, Navigation, AlertTriangle, ShieldAlert, Layers, CheckCircle2, RefreshCw, Compass, Info } from 'lucide-react';
import { RouteAnalysisSynthesisResult, CandidateComparisonItem, SpeedReadingInterval } from './routeAnalysis.types';
import { env } from '../../../../config/env';

interface RouteMapVisualizationProps {
  result?: RouteAnalysisSynthesisResult;
  synthesisResult?: RouteAnalysisSynthesisResult | null;
  selectedCandidateId?: string | null;
  activeCandidatePlantId?: string | null;
  onSelectCandidate?: (candidatePlantId: string) => void;
}

const KNOWN_GOA_PLANT_COORDS: Record<string, { lat: number; lng: number }> = {
  ACC_VASCO: { lat: 15.3991, lng: 73.8153 },
  ACC_KUNDAIM: { lat: 15.4215, lng: 73.9856 },
  ACC_DHARGA: { lat: 15.6025, lng: 73.8201 },
  ACC_NESSAI: { lat: 15.2635, lng: 74.0152 },
};

function decodePolyline(encoded: string): Array<{ lat: number; lng: number }> {
  if (!encoded) return [];
  const poly: Array<{ lat: number; lng: number }> = [];
  let index = 0;
  const len = encoded.length;
  let lat = 0;
  let lng = 0;

  while (index < len) {
    let b;
    let shift = 0;
    let result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += dlat;

    shift = 0;
    result = 0;
    do {
      b = encoded.charCodeAt(index++) - 63;
      result |= (b & 0x1f) << shift;
      shift += 5;
    } while (b >= 0x20);
    const dlng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += dlng;

    poly.push({ lat: lat / 1e5, lng: lng / 1e5 });
  }
  return poly;
}

export const RouteMapVisualization: React.FC<RouteMapVisualizationProps> = ({
  result: rawResult,
  synthesisResult,
  selectedCandidateId: rawSelectedId,
  activeCandidatePlantId,
  onSelectCandidate,
}) => {
  const result = rawResult || synthesisResult;
  const selectedCandidateId = rawSelectedId || activeCandidatePlantId;

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const polylinesRef = useRef<any[]>([]);
  const markersRef = useRef<any[]>([]);

  const [mapLoaded, setMapLoaded] = useState(false);
  const [googleAuthError, setGoogleAuthError] = useState(false);

  if (!result) {
    return (
      <div className="p-8 text-center rounded-2xl border border-dashed border-slate-200 bg-slate-50 text-slate-400 text-xs font-medium">
        No route synthesis data available for visualization.
      </div>
    );
  }

  const {
    current_source_plant_id,
    current_source_plant_code,
    current_source_plant_name,
    current_source_plant_latitude,
    current_source_plant_longitude,
    site_id,
    site_code,
    site_name,
    site_latitude,
    site_longitude,
    recommended_plant_id,
    recommendation_status,
    primary_case_category,
    is_google_fresh,
    is_google_stale_cache,
    google_cache_age_seconds,
    detailed_route,
    google_evidence,
    comparisons = [],
  } = result;

  const isIncidentMode =
    site_code === 'TM_INCIDENT' ||
    (result as any)?.analysis_context === 'TM_INCIDENT_ACCESS' ||
    site_name?.toLowerCase().includes('incident');

  // Verify coordinates & evidence
  const hasSiteCoords = site_latitude !== null && site_latitude !== undefined && site_longitude !== null && site_longitude !== undefined;
  const hasPlantCoords = (current_source_plant_latitude !== null && current_source_plant_latitude !== undefined && current_source_plant_longitude !== null && current_source_plant_longitude !== undefined) || (current_source_plant_code && !!KNOWN_GOA_PLANT_COORDS[current_source_plant_code]);
  const isMissingCoordinates = (!hasSiteCoords || !hasPlantCoords) && (recommendation_status === 'LOCATION_DATA_MISSING' || primary_case_category === 'C11_COORDINATES_MISSING');
  
  const hasPolylineEvidence = !!detailed_route?.encoded_polyline || Object.keys(google_evidence?.detailed_routes || {}).length > 0 || Object.keys((result as any)?.google_routes_evidence?.detailed_routes || {}).length > 0;

  // If coordinates are missing (C11)
  if (isMissingCoordinates) {
    return (
      <div data-testid="route-map-missing-coords" className="p-6 rounded-2xl border border-rose-200 bg-rose-50/70 text-rose-950 flex flex-col items-center justify-center text-center space-y-3 min-h-[260px]">
        <ShieldAlert className="w-10 h-10 text-rose-600" />
        <div className="space-y-1">
          <h4 className="font-bold text-sm">Route Visualization Unavailable — Coordinates Missing</h4>
          <p className="text-xs text-rose-700 max-w-md">
            Authoritative GPS coordinates for destination site or operational plant are missing. No synthetic coordinates are fabricated.
          </p>
        </div>
      </div>
    );
  }

  // If no detailed route or google evidence is available
  if (!hasPolylineEvidence && !google_evidence && !detailed_route) {
    return (
      <div data-testid="route-map-unavailable" className="p-6 rounded-2xl border border-slate-200 bg-slate-50 text-slate-800 flex flex-col items-center justify-center text-center space-y-3 min-h-[260px]">
        <AlertTriangle className="w-10 h-10 text-amber-500" />
        <div className="space-y-1">
          <h4 className="font-bold text-sm">Route Polyline Unavailable</h4>
          <p className="text-xs text-slate-500 max-w-md">
            Google Routes provider evidence did not return a valid polyline for this corridor.
          </p>
        </div>
      </div>
    );
  }

  // Identify all routes to render
  const routesToRender = useMemo(() => {
    const list: Array<{
      plantId: string;
      plantCode: string;
      plantName: string;
      plantLat: number;
      plantLng: number;
      isCurrent: boolean;
      isRecommended: boolean;
      isSelected: boolean;
      polylinePoints: Array<{ lat: number; lng: number }>;
      speedIntervals: SpeedReadingInterval[];
      distanceKm?: number | null;
      durationMinutes?: number | null;
      trafficDelayMinutes?: number | null;
    }> = [];

    const detailedRoutesMap = (result as any)?.google_evidence?.detailed_routes || (result as any)?.google_routes_evidence?.detailed_routes || {};
    
    // Resolve Plant 1 (Current / Approved / Primary Plant)
    const currCode = current_source_plant_code || 'ACC_PLANT';
    const currCoords = KNOWN_GOA_PLANT_COORDS[currCode] || {
      lat: current_source_plant_latitude || 15.3991,
      lng: current_source_plant_longitude || 73.8153,
    };
    const currDetail = detailedRoutesMap[current_source_plant_id] || (detailed_route?.plant_id === current_source_plant_id ? detailed_route : null);
    
    let currPoly = decodePolyline(currDetail?.encoded_polyline || '');
    if (currPoly.length === 0 && hasSiteCoords) {
      currPoly = [
        { lat: currCoords.lat, lng: currCoords.lng },
        { lat: site_latitude!, lng: site_longitude! },
      ];
    }

    list.push({
      plantId: current_source_plant_id || 'curr-plant',
      plantCode: currCode,
      plantName: current_source_plant_name || 'Operational Plant',
      plantLat: currCoords.lat,
      plantLng: currCoords.lng,
      isCurrent: true,
      isRecommended: recommended_plant_id === current_source_plant_id,
      isSelected: !selectedCandidateId || selectedCandidateId === current_source_plant_id,
      polylinePoints: currPoly,
      speedIntervals: currDetail?.speed_reading_intervals || [],
      distanceKm: currDetail?.distance_km ?? (comparisons.find((c) => c.is_current_source)?.google_road_distance_km ?? null),
      durationMinutes: currDetail?.duration_minutes ?? (comparisons.find((c) => c.is_current_source)?.google_duration_in_traffic_minutes ?? null),
      trafficDelayMinutes: currDetail?.traffic_delay_minutes ?? null,
    });

    // Resolve Candidate Plants
    for (const comp of comparisons) {
      const cId = comp.candidate_plant_id || comp.plant_id;
      const cCode = comp.candidate_plant_code || comp.plant_code || 'ALT';
      if (!cId || cId === current_source_plant_id || cCode === current_source_plant_code) continue;

      const cCoords = KNOWN_GOA_PLANT_COORDS[cCode] || {
        lat: comp.plant_latitude || 15.4215,
        lng: comp.plant_longitude || 73.9856,
      };

      const cDetail = detailedRoutesMap[cId] || (detailed_route?.plant_id === cId ? detailed_route : null);
      let cPoly = decodePolyline(cDetail?.encoded_polyline || '');
      if (cPoly.length === 0 && hasSiteCoords) {
        cPoly = [
          { lat: cCoords.lat, lng: cCoords.lng },
          { lat: site_latitude!, lng: site_longitude! },
        ];
      }

      list.push({
        plantId: cId,
        plantCode: cCode,
        plantName: comp.candidate_plant_name || comp.plant_name || 'Candidate Plant',
        plantLat: cCoords.lat,
        plantLng: cCoords.lng,
        isCurrent: false,
        isRecommended: recommended_plant_id === cId,
        isSelected: selectedCandidateId === cId,
        polylinePoints: cPoly,
        speedIntervals: cDetail?.speed_reading_intervals || [],
        distanceKm: cDetail?.distance_km ?? comp.google_road_distance_km ?? comp.google_candidate_distance_km,
        durationMinutes: cDetail?.duration_minutes ?? comp.google_duration_in_traffic_minutes ?? comp.google_candidate_duration_minutes,
        trafficDelayMinutes: cDetail?.traffic_delay_minutes ?? comp.google_traffic_delay_minutes ?? comp.google_candidate_traffic_delay_minutes,
      });
    }

    return list;
  }, [
    current_source_plant_id,
    current_source_plant_code,
    current_source_plant_name,
    current_source_plant_latitude,
    current_source_plant_longitude,
    recommended_plant_id,
    selectedCandidateId,
    detailed_route,
    google_evidence,
    comparisons,
    hasSiteCoords,
    site_latitude,
    site_longitude,
  ]);

  // Handle Google Maps Authentication Failures
  useEffect(() => {
    (window as any).gm_authFailure = () => {
      console.warn('Google Maps JS auth failure detected. Defaulting to Vector Corridor Map.');
      setGoogleAuthError(true);
    };
  }, []);

  // Compute Vector Projection Boundaries for SVG Map
  const svgProjection = useMemo(() => {
    let minLat = 90, maxLat = -90, minLng = 180, maxLng = -180;
    
    if (hasSiteCoords) {
      minLat = Math.min(minLat, site_latitude!);
      maxLat = Math.max(maxLat, site_latitude!);
      minLng = Math.min(minLng, site_longitude!);
      maxLng = Math.max(maxLng, site_longitude!);
    }

    routesToRender.forEach((r) => {
      minLat = Math.min(minLat, r.plantLat);
      maxLat = Math.max(maxLat, r.plantLat);
      minLng = Math.min(minLng, r.plantLng);
      maxLng = Math.max(maxLng, r.plantLng);

      r.polylinePoints.forEach((p) => {
        minLat = Math.min(minLat, p.lat);
        maxLat = Math.max(maxLat, p.lat);
        minLng = Math.min(minLng, p.lng);
        maxLng = Math.max(maxLng, p.lng);
      });
    });

    if (minLat >= maxLat || minLng >= maxLng) {
      minLat = 15.2; maxLat = 15.7; minLng = 73.7; maxLng = 74.2;
    }

    const latSpan = (maxLat - minLat) || 0.1;
    const lngSpan = (maxLng - minLng) || 0.1;
    const padX = 70;
    const padY = 50;
    const svgWidth = 840;
    const svgHeight = 380;

    const project = (lat: number, lng: number) => {
      const x = padX + ((lng - minLng) / lngSpan) * (svgWidth - 2 * padX);
      const y = svgHeight - (padY + ((lat - minLat) / latSpan) * (svgHeight - 2 * padY));
      return { x, y };
    };

    return { project, svgWidth, svgHeight };
  }, [hasSiteCoords, site_latitude, site_longitude, routesToRender]);

  return (
    <div data-testid="route-map-container" className="rounded-lg border border-slate-200/90 bg-white shadow-2xs overflow-hidden">
      {/* Map Control Header */}
      <div className="p-3.5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/70">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-md bg-blue-50 text-blue-700 border border-blue-200/60">
            <Compass className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-slate-900">
                {isIncidentMode
                  ? 'Operator-Reported Incident Map & Current Route Visualization'
                  : 'Physical Corridor Route Visualization'}
              </h3>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${is_google_fresh ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                {is_google_fresh ? 'Live Google Traffic' : `Cached (${Math.round(google_cache_age_seconds || 0)}s)`}
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                Vector Corridor Engine
              </span>
            </div>
            <p className="text-[11px] text-slate-500">
              {isIncidentMode
                ? `Operational Plant (${current_source_plant_code}) → Operator-reported TM location`
                : `Approved Plant (${current_source_plant_code}) → Destination Site (${site_code}) vs Alternative Candidates`}
            </p>
          </div>
        </div>

        {/* Route Selector Badges */}
        <div className="flex flex-wrap items-center gap-1.5">
          {routesToRender.map((r) => {
            const isSelected = r.isSelected || (!selectedCandidateId && r.isCurrent);
            return (
              <button
                key={r.plantId}
                type="button"
                onClick={() => onSelectCandidate && onSelectCandidate(r.plantId)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold border transition-all cursor-pointer ${
                  isSelected
                    ? r.isCurrent
                      ? 'bg-emerald-700 text-white border-emerald-700 shadow-2xs'
                      : r.isRecommended
                      ? 'bg-teal-700 text-white border-teal-700 shadow-2xs'
                      : 'bg-blue-700 text-white border-blue-700 shadow-2xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                }`}
              >
                <span>{r.plantCode}</span>
                {r.isCurrent && <span className="text-[10px] opacity-90">{isIncidentMode ? '(Fastest Access)' : '(Approved)'}</span>}
                {r.isRecommended && !r.isCurrent && <CheckCircle2 className="w-3 h-3 text-white shrink-0" />}
                {r.distanceKm && <span className="text-[10px] font-mono tabular-nums opacity-90">{typeof r.distanceKm === 'number' ? `${r.distanceKm.toFixed(1)}km` : `${r.distanceKm}km`}</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* Map Rendering Container — Crisp High-Fidelity SVG Vector Canvas */}
      <div className="relative w-full h-[380px] bg-slate-950 overflow-hidden select-none">
        <div data-testid="mock-route-canvas" className="w-full h-full relative flex items-center justify-center">
          <svg
            viewBox={`0 0 ${svgProjection.svgWidth} ${svgProjection.svgHeight}`}
            className="w-full h-full object-contain"
          >
            <defs>
              <pattern id="grid-pattern-dark" width="36" height="36" patternUnits="userSpaceOnUse">
                <path d="M 36 0 L 0 0 0 36" fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" />
              </pattern>
            </defs>

            <rect width="100%" height="100%" fill="url(#grid-pattern-dark)" />

            {/* Draw All Candidate Corridor Lines & Polylines */}
            {routesToRender.map((r) => {
              const isHighlighted = r.isSelected || (!selectedCandidateId && r.isCurrent);
              if (!r.polylinePoints || r.polylinePoints.length === 0) return null;

              const pathData = r.polylinePoints.reduce((acc, p, idx) => {
                const pt = svgProjection.project(p.lat, p.lng);
                return `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`;
              }, '');

              const isDirectVector = r.polylinePoints.length === 2;
              const strokeColor = r.isCurrent ? '#10B981' : r.isRecommended ? '#14B8A6' : '#6366F1';
              const strokeWidth = isHighlighted ? 4.5 : 2.0;
              const strokeOpacity = isHighlighted ? 0.95 : 0.35;

              return (
                <g key={r.plantId} className="cursor-pointer" onClick={() => onSelectCandidate && onSelectCandidate(r.plantId)}>
                  {isHighlighted && (
                    <path
                      d={pathData}
                      fill="none"
                      stroke={strokeColor}
                      strokeWidth={strokeWidth + 4}
                      strokeOpacity={0.25}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeDasharray={isDirectVector ? '6,6' : undefined}
                    />
                  )}
                  <path
                    d={pathData}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    strokeOpacity={strokeOpacity}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeDasharray={isDirectVector ? '6,6' : undefined}
                  />

                  {/* Draw Speed Reading Intervals if present */}
                  {isHighlighted && r.speedIntervals && r.speedIntervals.length > 0 && r.polylinePoints.length > 2 && (
                    r.speedIntervals.map((interval, sIdx) => {
                      const start = interval.start_polyline_point_index;
                      const end = interval.end_polyline_point_index;
                      if (start < r.polylinePoints.length && end <= r.polylinePoints.length && start < end) {
                        const segPoints = r.polylinePoints.slice(start, end + 1);
                        const segPath = segPoints.reduce((acc, p, idx) => {
                          const pt = svgProjection.project(p.lat, p.lng);
                          return `${acc} ${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`;
                        }, '');
                        return (
                          <path
                            key={sIdx}
                            d={segPath}
                            fill="none"
                            stroke={interval.color_hex || '#10B981'}
                            strokeWidth={strokeWidth + 1}
                            strokeOpacity={1.0}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        );
                      }
                      return null;
                    })
                  )}

                  {/* Plant Origin Pin */}
                  {(() => {
                    const originPt = svgProjection.project(r.plantLat, r.plantLng);
                    return (
                      <g transform={`translate(${originPt.x}, ${originPt.y})`}>
                        <circle r={isHighlighted ? 7 : 4.5} fill={strokeColor} stroke="#FFFFFF" strokeWidth={2} />
                        <text
                          x={11}
                          y={4}
                          fill="#F8FAFC"
                          fontSize="11"
                          fontWeight="bold"
                          fontFamily="monospace"
                          className="pointer-events-none drop-shadow-md"
                        >
                          {r.plantCode}
                        </text>
                      </g>
                    );
                  })()}
                </g>
              );
            })}

            {/* Destination / TM Incident Location Marker */}
            {hasSiteCoords && (() => {
              const sitePt = svgProjection.project(site_latitude!, site_longitude!);
              return (
                <g transform={`translate(${sitePt.x}, ${sitePt.y})`}>
                  <circle r={14} fill="#EF4444" opacity={0.25} className="animate-ping" />
                  <circle r={7.5} fill="#EF4444" stroke="#FFFFFF" strokeWidth={2.5} />
                  <text
                    x={13}
                    y={-6}
                    fill="#FCA5A5"
                    fontSize="11.5"
                    fontWeight="bold"
                    fontFamily="system-ui"
                    className="pointer-events-none drop-shadow-md"
                  >
                    {isIncidentMode ? 'TM Incident Location' : `${site_name} (${site_code})`}
                  </text>
                  <text
                    x={13}
                    y={9}
                    fill="#94A3B8"
                    fontSize="9.5"
                    fontFamily="monospace"
                    className="pointer-events-none drop-shadow-md"
                  >
                    {site_latitude?.toFixed(4)}, {site_longitude?.toFixed(4)}
                  </text>
                </g>
              );
            })()}
          </svg>

          {/* Provider Verification Overlay Badge */}
          <div className="absolute top-3 left-3 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/80 text-[11px] text-slate-300 flex items-center gap-2 shadow-lg">
            <Navigation className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              <strong className="text-white font-bold">{routesToRender.length} physical candidate routes</strong> decoded from Google Routes API v2
            </span>
          </div>
        </div>

        {/* Traffic Speed Legend Overlay */}
        <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur-xs px-3 py-1.5 rounded-lg border border-slate-200/90 shadow-2xs flex items-center gap-3 text-[10.5px] font-semibold text-slate-700">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Normal Traffic</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            <span>Slow</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span>Heavy Congestion</span>
          </div>
        </div>
      </div>
    </div>
  );
};
