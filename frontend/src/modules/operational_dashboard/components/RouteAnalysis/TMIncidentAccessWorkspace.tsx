import React, { useState } from 'react';
import {
  AlertTriangle,
  Navigation,
  RefreshCw,
  Clock,
  MapPin,
  Compass,
  FileText,
  Truck,
  ShieldCheck,
  ChevronRight,
  Info,
} from 'lucide-react';
import {
  useOperationalPlants,
  useExecuteTMIncidentAccess,
} from '../../hooks/useRouteAnalysis';
import {
  TMIncidentAccessResult,
  PlantIncidentAccessItem,
  RouteAnalysisSynthesisResult,
} from './routeAnalysis.types';
import { RouteMapVisualization } from './RouteMapVisualization';

const DEFAULT_OPERATIONAL_GOA_PLANTS = [
  { plant_id: 'acc_vasco', plant_code: 'ACC_VASCO', plant_name: 'ACC VASCO' },
  { plant_id: 'acc_kundaim', plant_code: 'ACC_KUNDAIM', plant_name: 'ACC KUNDAIM' },
  { plant_id: 'acc_dharga', plant_code: 'ACC_DHARGA', plant_name: 'ACC DHARGA' },
  { plant_id: 'acc_nessai', plant_code: 'ACC_NESSAI', plant_name: 'ACC NESSAI' },
];

export const TMIncidentAccessWorkspace: React.FC = () => {
  // Input fields
  const [latStr, setLatStr] = useState<string>('15.4989');
  const [lngStr, setLngStr] = useState<string>('73.8278');
  const [locationName, setLocationName] = useState<string>('Panaji City Center / Mandovi Junction');
  const [dispatchRef, setDispatchRef] = useState<string>('');
  const [vehicleRef, setVehicleRef] = useState<string>('');
  const [notes, setNotes] = useState<string>('Driver reported heavy congestion on approach bridge');
  const [forceRefresh, setForceRefresh] = useState<boolean>(false);

  // Analysis result state
  const [analysisResult, setAnalysisResult] = useState<TMIncidentAccessResult | null>(null);
  const [selectedCandidatePlantId, setSelectedCandidatePlantId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Hooks
  const { data: plantsData, isLoading: isLoadingPlants } = useOperationalPlants();
  const executeAnalysisMutation = useExecuteTMIncidentAccess();

  // Safely resolve plants list
  const operationalPlants = Array.isArray(plantsData?.plants)
    ? plantsData.plants
    : DEFAULT_OPERATIONAL_GOA_PLANTS;

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const lat = parseFloat(latStr);
    const lng = parseFloat(lngStr);

    if (isNaN(lat) || isNaN(lng)) {
      setFormError('Please enter valid numeric latitude and longitude coordinates.');
      return;
    }

    if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
      setFormError('Latitude must be between -90 and 90, and longitude between -180 and 180.');
      return;
    }

    try {
      const response = await executeAnalysisMutation.mutateAsync({
        reported_latitude: lat,
        reported_longitude: lng,
        reported_location_name: locationName.trim() || undefined,
        dispatch_reference: dispatchRef.trim() || undefined,
        vehicle_reference: vehicleRef.trim() || undefined,
        operator_notes: notes.trim() || undefined,
        force_refresh: forceRefresh,
      });

      if (response && response.success && response.data) {
        setAnalysisResult(response.data);
        if (response.data.best_access_plant_id) {
          setSelectedCandidatePlantId(response.data.best_access_plant_id);
        } else if (response.data.candidate_access_matrix && response.data.candidate_access_matrix.length > 0) {
          setSelectedCandidatePlantId(response.data.candidate_access_matrix[0].plant_id);
        }
      }
    } catch (err: any) {
      setFormError(err.message || 'Failed to execute incident access analysis.');
    }
  };

  // Convert TMIncidentAccessResult into RouteAnalysisSynthesisResult structure for RouteMapVisualization
  const sortedCandidates = [...(analysisResult?.candidate_access_matrix || [])].sort(
    (a, b) => (a.ranking ?? 999) - (b.ranking ?? 999)
  );

  const mapSynthesisData: RouteAnalysisSynthesisResult | null = analysisResult
    ? {
        analysis_id: analysisResult.analysis_id,
        site_id: 'OPERATOR_REPORTED_INCIDENT',
        site_code: 'TM_INCIDENT',
        site_name: analysisResult.reported_location_name || 'Operator-reported TM location',
        site_latitude: analysisResult.reported_latitude,
        site_longitude: analysisResult.reported_longitude,
        current_source_plant_id: analysisResult.best_access_plant_id || (operationalPlants[0]?.plant_id || ''),
        current_source_plant_code: analysisResult.best_access_plant_code || '',
        current_source_plant_name: analysisResult.best_access_plant_name || '',
        current_source_plant_latitude: operationalPlants.find(p => p.plant_id === analysisResult.best_access_plant_id)?.latitude ?? 15.3991,
        current_source_plant_longitude: operationalPlants.find(p => p.plant_id === analysisResult.best_access_plant_id)?.longitude ?? 73.8153,
        recommended_plant_id: analysisResult.best_access_plant_id,
        recommended_plant_code: analysisResult.best_access_plant_code,
        recommended_plant_name: analysisResult.best_access_plant_name,
        evaluation_mode: 'NOW',
        analysis_timestamp: analysisResult.analysis_timestamp,
        decision_state: analysisResult.decision_state as any,
        decision_summary: analysisResult.decision_summary,
        detailed_reasoning: analysisResult.operational_advisory,
        historical_evidence: {
          status: analysisResult.historical_evidence_status,
          sample_count: 0,
          mean_transit_duration_minutes: null,
          median_transit_duration_minutes: null,
          p90_transit_duration_minutes: null,
          min_transit_duration_minutes: null,
          max_transit_duration_minutes: null,
          data_window_days: 90,
          route_corridor: `Operator Reported TM Location (${analysisResult.reported_latitude.toFixed(4)}, ${analysisResult.reported_longitude.toFixed(4)})`,
        },
        google_evidence: {
          status: 'FETCHED',
          mode: 'NOW',
          response_timestamp: analysisResult.google_queried_at || analysisResult.analysis_timestamp,
          is_fresh: analysisResult.is_google_fresh,
          is_stale_cache: analysisResult.is_google_stale_cache,
          cache_age_seconds: analysisResult.google_cache_age_seconds,
          matrix_items: (analysisResult.candidate_access_matrix || []).reduce((acc: any, c: PlantIncidentAccessItem) => {
            acc[c.plant_id] = {
              candidate_plant_id: c.plant_id,
              candidate_plant_code: c.plant_code,
              candidate_plant_name: c.plant_name,
              distance_km: c.road_distance_km ?? c.distance_meters / 1000,
              duration_minutes: c.duration_minutes ?? c.duration_seconds / 60,
              duration_in_traffic_minutes: c.duration_minutes ?? c.duration_seconds / 60,
              static_duration_minutes: c.static_duration_seconds ? c.static_duration_seconds / 60 : null,
              traffic_delay_minutes: c.traffic_delay_minutes ?? 0,
              condition: 'OPTIMAL',
              status: 'OK',
            };
            return acc;
          }, {}),
          detailed_routes: (analysisResult.candidate_access_matrix || []).reduce((acc: any, c: any) => {
            const dRoute = c.detailed_route;
            const polyline = dRoute?.encoded_polyline || c.polyline || '';
            if (polyline) {
              acc[c.plant_id] = {
                candidate_plant_id: c.plant_id,
                candidate_plant_code: c.plant_code,
                plant_id: c.plant_id,
                plant_code: c.plant_code,
                encoded_polyline: polyline,
                distance_km: dRoute?.distance_km ?? c.road_distance_km ?? 0,
                duration_minutes: dRoute?.duration_minutes ?? c.duration_minutes ?? 0,
                duration_in_traffic_minutes: dRoute?.duration_minutes ?? c.duration_minutes ?? 0,
                static_duration_minutes: dRoute?.static_duration_minutes ?? c.static_duration_minutes ?? null,
                traffic_delay_minutes: dRoute?.traffic_delay_minutes ?? c.traffic_delay_minutes ?? 0,
                speed_reading_intervals: (dRoute?.speed_reading_intervals || c.speed_intervals || []).map((si: any) => ({
                  start_index: si.start_index,
                  end_index: si.end_index,
                  speed_category: si.speed_category || si.speed,
                })),
                speed_intervals: (dRoute?.speed_reading_intervals || c.speed_intervals || []).map((si: any) => ({
                  start_index: si.start_index,
                  end_index: si.end_index,
                  speed_category: si.speed_category || si.speed,
                })),
                steps: [],
                status: 'OK',
              };
            }
            return acc;
          }, {}),
        },
        google_routes_evidence: {
          status: 'FETCHED',
          mode: 'NOW',
          response_timestamp: analysisResult.google_queried_at || analysisResult.analysis_timestamp,
          is_fresh: analysisResult.is_google_fresh,
          is_stale_cache: analysisResult.is_google_stale_cache,
          cache_age_seconds: analysisResult.google_cache_age_seconds,
          matrix_items: (analysisResult.candidate_access_matrix || []).reduce((acc: any, c: PlantIncidentAccessItem) => {
            acc[c.plant_id] = {
              candidate_plant_id: c.plant_id,
              candidate_plant_code: c.plant_code,
              candidate_plant_name: c.plant_name,
              distance_km: c.road_distance_km ?? c.distance_meters / 1000,
              duration_minutes: c.duration_minutes ?? c.duration_seconds / 60,
              duration_in_traffic_minutes: c.duration_minutes ?? c.duration_seconds / 60,
              static_duration_minutes: c.static_duration_seconds ? c.static_duration_seconds / 60 : null,
              traffic_delay_minutes: c.traffic_delay_minutes ?? 0,
              condition: 'OPTIMAL',
              status: 'OK',
            };
            return acc;
          }, {}),
          detailed_routes: (analysisResult.candidate_access_matrix || []).reduce((acc: any, c: any) => {
            const dRoute = c.detailed_route;
            const polyline = dRoute?.encoded_polyline || c.polyline || '';
            if (polyline) {
              acc[c.plant_id] = {
                candidate_plant_id: c.plant_id,
                candidate_plant_code: c.plant_code,
                plant_id: c.plant_id,
                plant_code: c.plant_code,
                encoded_polyline: polyline,
                distance_km: dRoute?.distance_km ?? c.road_distance_km ?? 0,
                duration_minutes: dRoute?.duration_minutes ?? c.duration_minutes ?? 0,
                duration_in_traffic_minutes: dRoute?.duration_minutes ?? c.duration_minutes ?? 0,
                static_duration_minutes: dRoute?.static_duration_minutes ?? c.static_duration_minutes ?? null,
                traffic_delay_minutes: dRoute?.traffic_delay_minutes ?? c.traffic_delay_minutes ?? 0,
                speed_reading_intervals: (dRoute?.speed_reading_intervals || c.speed_intervals || []).map((si: any) => ({
                  start_index: si.start_index,
                  end_index: si.end_index,
                  speed_category: si.speed_category || si.speed,
                })),
                speed_intervals: (dRoute?.speed_reading_intervals || c.speed_intervals || []).map((si: any) => ({
                  start_index: si.start_index,
                  end_index: si.end_index,
                  speed_category: si.speed_category || si.speed,
                })),
                steps: [],
                status: 'OK',
              };
            }
            return acc;
          }, {}),
        },
        comparisons: (analysisResult.candidate_access_matrix || []).map((c: PlantIncidentAccessItem) => ({
          candidate_plant_id: c.plant_id,
          candidate_plant_code: c.plant_code,
          candidate_plant_name: c.plant_name,
          crow_fly_distance_km: c.crow_fly_distance_km,
          google_road_distance_km: c.road_distance_km,
          google_duration_in_traffic_minutes: c.duration_minutes,
          google_traffic_delay_minutes: c.traffic_delay_minutes,
          historical_mean_duration_minutes: null,
          historical_sample_count: 0,
          historical_advantage_minutes: null,
          google_advantage_minutes:
            c.duration_minutes !== null && analysisResult.best_access_eta_minutes !== null
              ? analysisResult.best_access_eta_minutes - c.duration_minutes
              : null,
          is_recommended: c.is_best_access,
          is_current_source: false,
          rank: c.ranking ?? 0,
        })),
        engine_version: analysisResult.engine_version,
        policy_version: analysisResult.policy_version,
      }
    : null;

  return (
    <div className="space-y-5">
      {/* Header Banner - Strict Light Theme */}
      <div className="p-4 rounded-lg border border-slate-200/90 bg-white shadow-2xs">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-lg bg-amber-50 text-amber-700 border border-amber-200/80">
              <AlertTriangle className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900">
                  TM Incident / Stuck TM Current-Traffic Decision Support
                </h2>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Live Traffic Engine v1.2.1
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5 font-medium">
                Evaluate current Google Routes road travel times across all 4 operational Goa plants to determine shortest road ETA to an operator-reported stuck TM location.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-md border border-slate-200 text-xs font-semibold text-slate-600 shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-blue-700" />
            <span>Decision Support Only • No Truck GPS • No Auto Dispatch</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Operator Input Form */}
        <div className="lg:col-span-5 rounded-lg border border-slate-200/90 bg-white shadow-2xs p-4 space-y-3.5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-blue-700" />
              Operator Incident Report Input
            </h3>
            <span className="text-[10px] text-slate-400 font-mono font-semibold">
              Real Coordinates
            </span>
          </div>

          <form onSubmit={handleAnalyze} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Reported Latitude <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={latStr}
                  onChange={(e) => setLatStr(e.target.value)}
                  placeholder="e.g. 15.4989"
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Reported Longitude <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={lngStr}
                  onChange={(e) => setLngStr(e.target.value)}
                  placeholder="e.g. 73.8278"
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Reported Landmark / Location Name (Optional)
              </label>
              <input
                type="text"
                value={locationName}
                onChange={(e) => setLocationName(e.target.value)}
                placeholder="e.g. Panaji Mandovi Bridge / Porvorim Junction"
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600 transition"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Dispatch # (Optional)
                </label>
                <input
                  type="text"
                  value={dispatchRef}
                  onChange={(e) => setDispatchRef(e.target.value)}
                  placeholder="e.g. DSP-2026-9812"
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Vehicle / TM # (Optional)
                </label>
                <input
                  type="text"
                  value={vehicleRef}
                  onChange={(e) => setVehicleRef(e.target.value)}
                  placeholder="e.g. GA-08-V-1234"
                  className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Incident Notes
              </label>
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Details of driver report, bottleneck, breakdown..."
                className="w-full px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-600 transition resize-none"
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="forceRefresh"
                checked={forceRefresh}
                onChange={(e) => setForceRefresh(e.target.checked)}
                className="rounded border-slate-300 text-blue-700 focus:ring-blue-600 w-3.5 h-3.5 cursor-pointer"
              />
              <label htmlFor="forceRefresh" className="text-xs text-slate-600 cursor-pointer select-none font-medium">
                Bypass Cache (Force Fresh Google Call)
              </label>
            </div>

            {formError && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-md text-xs text-rose-700 font-medium">
                {formError}
              </div>
            )}

            <button
              id="analyze-plant-access-btn"
              data-testid="btn-analyze-incident"
              type="submit"
              disabled={executeAnalysisMutation.isPending}
              className="w-full py-2 px-4 bg-blue-700 hover:bg-blue-800 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-2 shadow-2xs transition disabled:opacity-50 cursor-pointer"
            >
              {executeAnalysisMutation.isPending ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Evaluating Live Google Traffic...</span>
                </>
              ) : (
                <>
                  <Navigation className="w-3.5 h-3.5" />
                  <span>Analyze Current Plant Access</span>
                </>
              )}
            </button>
          </form>

          {/* Master Goa Plants List Preview */}
          <div className="pt-3 border-t border-slate-100 space-y-2">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Evaluated Master Plants ({operationalPlants.length})
            </div>
            <div className="grid grid-cols-2 gap-2">
              {operationalPlants.map((p: any) => (
                <div
                  key={p.plant_id || p.plant_code}
                  className="p-2 bg-slate-50 border border-slate-200 rounded-md text-[11px] text-slate-700 flex items-center justify-between"
                >
                  <span className="font-bold text-slate-800 font-mono">{p.plant_code}</span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Decision Support Results & Ranking */}
        <div className="lg:col-span-7 space-y-4">
          {analysisResult ? (
            <>
              {/* Best Access Summary Card */}
              <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50/50 shadow-2xs relative overflow-hidden">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 bg-emerald-700 text-white rounded-md text-[10px] font-mono font-bold tracking-wider uppercase">
                        Fastest Access Plant
                      </span>
                      <span className="text-xs font-mono font-semibold text-slate-500">
                        {new Date(analysisResult.analysis_timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-lg font-extrabold text-slate-900 mt-1">
                      {analysisResult.best_access_plant_name} ({analysisResult.best_access_plant_code})
                    </div>
                    <p className="text-xs text-slate-600 mt-1 font-medium">
                      {analysisResult.decision_summary}
                    </p>
                  </div>

                  <div className="text-right sm:border-l sm:border-emerald-200 sm:pl-4">
                    <div className="text-xl font-black text-emerald-700 font-mono tabular-nums">
                      {analysisResult.best_access_eta_minutes !== null
                        ? `${analysisResult.best_access_eta_minutes.toFixed(1)} min`
                        : 'N/A'}
                    </div>
                    <div className="text-xs text-slate-500 font-mono tabular-nums font-semibold">
                      {analysisResult.best_access_distance_km !== null
                        ? `${analysisResult.best_access_distance_km.toFixed(1)} km road distance`
                        : ''}
                    </div>
                  </div>
                </div>

                <div className="mt-3.5 pt-2.5 border-t border-emerald-200/60 flex flex-wrap items-center justify-between text-xs text-slate-600 gap-2">
                  <div className="flex items-center gap-2">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      Traffic Source:{' '}
                      <span className="font-semibold text-slate-800">
                        {analysisResult.is_google_fresh
                          ? `Fresh • 0s`
                          : analysisResult.is_google_stale_cache
                          ? `Stale Cache • ${Math.round(analysisResult.google_cache_age_seconds || 0)}s old`
                          : `Cached • ${Math.round(analysisResult.google_cache_age_seconds || 0)}s old`}
                      </span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Info className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      Historical Baseline: <span className="font-mono font-semibold text-slate-700">INSUFFICIENT (Ad-hoc Incident)</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Operational Advisory Banner (Prominent Warning) */}
              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg flex items-start gap-2.5 text-xs text-amber-900 shadow-2xs">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-amber-900 font-bold">Operational Advisory Only: </strong>
                  <span>{analysisResult.operational_advisory}</span>
                </div>
              </div>

              {/* Candidate Access Comparison Table */}
              <div className="rounded-lg border border-slate-200/90 bg-white shadow-2xs overflow-hidden">
                <div className="p-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                    <Compass className="w-4 h-4 text-blue-700" />
                    Candidate Plant Access Ranking (Ranked by Google Road ETA)
                  </h4>
                  <span className="text-xs text-slate-500 font-mono font-semibold">
                    {analysisResult.candidate_access_matrix?.length || 0} Candidates
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-50 text-slate-700 uppercase font-mono text-[10px] border-b border-slate-200 font-bold">
                      <tr>
                        <th className="py-2.5 px-3">Rank</th>
                        <th className="py-2.5 px-3">Plant</th>
                        <th className="py-2.5 px-3 text-right">Road ETA</th>
                        <th className="py-2.5 px-3 text-right">Traffic Delay</th>
                        <th className="py-2.5 px-3 text-right">Road Dist</th>
                        <th className="py-2.5 px-3 text-right">Crow-Fly Dist</th>
                        <th className="py-2.5 px-3 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
                      {(sortedCandidates).map((c) => (
                        <tr
                          key={c.plant_id}
                          className={`hover:bg-slate-50/80 transition cursor-pointer ${
                            c.plant_id === selectedCandidatePlantId
                              ? 'bg-emerald-50/50 border-l-2 border-emerald-500'
                              : ''
                          }`}
                          onClick={() => setSelectedCandidatePlantId(c.plant_id)}
                        >
                          <td className="py-2.5 px-3 font-mono font-bold">
                            {c.is_best_access ? (
                              <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-md font-semibold text-[10px]">
                                #1 BEST
                              </span>
                            ) : (
                              <span className="text-slate-500">#{c.ranking ?? '-'}</span>
                            )}
                          </td>
                          <td className="py-2.5 px-3 font-sans">
                            <div className="font-bold text-slate-800">{c.plant_code}</div>
                            <div className="text-[11px] text-slate-500 font-medium">{c.plant_name}</div>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900 tabular-nums">
                            {c.duration_minutes !== null ? `${c.duration_minutes.toFixed(1)}m` : 'N/A'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-semibold text-amber-700 tabular-nums">
                            {c.traffic_delay_minutes !== null && c.traffic_delay_minutes > 0
                              ? `+${c.traffic_delay_minutes.toFixed(1)}m`
                              : '0.0m'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-700 tabular-nums">
                            {c.road_distance_km !== null ? `${c.road_distance_km.toFixed(1)} km` : 'N/A'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-slate-500 tabular-nums">
                            {c.crow_fly_distance_km?.toFixed(1) ?? 'N/A'} km
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <button
                              type="button"
                              className={`px-2 py-1 rounded-md text-[10.5px] font-semibold transition cursor-pointer ${
                                c.plant_id === selectedCandidatePlantId
                                  ? 'bg-blue-700 text-white shadow-2xs'
                                  : 'bg-white text-slate-700 hover:bg-slate-50 border border-slate-200'
                              }`}
                            >
                              View Route
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-white shadow-2xs p-8 text-center">
              <Navigation className="w-10 h-10 text-slate-300 mb-3" />
              <h4 className="text-sm font-bold text-slate-800">No Incident Analysis Yet</h4>
              <p className="text-xs text-slate-500 max-w-sm mt-1 font-medium">
                Enter the driver-reported coordinates on the left and click "Analyze Current Plant Access" to rank all 4 Goa operational plants by live road travel time.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Interactive Map Visualizer */}
      {mapSynthesisData && (
        <div className="rounded-lg border border-slate-200/90 bg-white shadow-2xs p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <Navigation className="w-4 h-4 text-blue-700" />
                Operator-Reported Incident Map &amp; Current Route Visualization
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5 font-medium">
                Marker: <strong className="text-emerald-700">Operator-reported TM location</strong>. Polylines show speed intervals from candidate plants.
              </p>
            </div>
            <div className="text-xs font-mono text-slate-500">
              Selected Candidate:{' '}
              <strong className="text-blue-700 font-bold">
                {analysisResult?.candidate_access_matrix?.find((c) => c.plant_id === selectedCandidatePlantId)
                  ?.plant_code || 'None'}
              </strong>
            </div>
          </div>

          <RouteMapVisualization
            result={mapSynthesisData}
            selectedCandidateId={selectedCandidatePlantId}
            onSelectCandidate={(plantId) => setSelectedCandidatePlantId(plantId)}
          />
        </div>
      )}
    </div>
  );
};
