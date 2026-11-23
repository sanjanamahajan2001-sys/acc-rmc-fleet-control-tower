import React from 'react';
import { CandidateComparisonItem } from './routeAnalysis.types';
import { Check, Star, Navigation, History } from 'lucide-react';

interface CandidateComparisonMatrixProps {
  comparisons?: CandidateComparisonItem[];
  candidates?: any[];
  currentPlantId?: string;
  winningPlantId?: string;
  recommendedPlantId?: string | null;
  selectedCandidateId?: string | null;
  onSelectCandidate?: (candidatePlantId: string) => void;
}

export const CandidateComparisonMatrix: React.FC<CandidateComparisonMatrixProps> = ({
  comparisons,
  candidates,
  currentPlantId,
  winningPlantId,
  recommendedPlantId,
  selectedCandidateId,
  onSelectCandidate,
}) => {
  const rawItems = comparisons || candidates || [];
  const targetRecId = recommendedPlantId || winningPlantId;

  if (!rawItems || rawItems.length === 0) {
    return (
      <div className="p-8 text-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 text-slate-500 text-sm">
        No candidate plant comparisons available for the current selection.
      </div>
    );
  }

  // Construct complete plant list including current plant
  const items: any[] = [];
  const firstItem: any = rawItems[0];
  const currId = currentPlantId || firstItem?.current_plant_id;

  if (currId && firstItem?.current_plant_code) {
    items.push({
      plant_id: currId,
      plant_code: firstItem.current_plant_code,
      plant_name: firstItem.current_plant_name || firstItem.current_plant_code,
      is_current_source: true,
      google_distance_km: firstItem.google_current_distance_km,
      google_duration_in_traffic_mins: firstItem.google_current_duration_minutes,
      google_traffic_delay_minutes: firstItem.google_current_traffic_delay_minutes ?? 0,
      historical_t1_p50_mins: firstItem.historical_current_p50_minutes,
      historical_sample_count: firstItem.historical_current_sample_count ?? 0,
      historical_confidence: firstItem.historical_current_confidence,
    });
  }

  for (const c of rawItems) {
    items.push(c);
  }

  return (
    <div className="rounded-lg border border-slate-200/90 bg-white shadow-2xs overflow-hidden">
      <div className="p-3.5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/70">
        <div>
          <h3 className="text-sm font-bold text-slate-900">Candidate Plant Comparison Matrix</h3>
          <p className="text-[11px] font-medium text-slate-500">
            Dual-evidence comparison: Real Google Routes traffic estimates + Authoritative ERP T1 historical transit
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Recommended
          </span>
          <span className="flex items-center gap-1 ml-2">
            <span className="w-2 h-2 rounded-full bg-blue-600" /> Current Approved
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-slate-700 font-bold uppercase tracking-wider text-[10.5px]">
              <th className="py-3 px-4">Plant Origin</th>
              <th className="py-3 px-3">Role / Status</th>
              <th className="py-3 px-3 text-right">Crow-Fly</th>
              <th className="py-3 px-3 text-right">
                <span className="flex items-center justify-end gap-1">
                  <Navigation className="w-3 h-3 text-blue-600" /> Google Dist
                </span>
              </th>
              <th className="py-3 px-3 text-right">
                <span className="flex items-center justify-end gap-1">
                  <Navigation className="w-3 h-3 text-blue-600" /> Traffic ETA
                </span>
              </th>
              <th className="py-3 px-3 text-right">Traffic Delay</th>
              <th className="py-3 px-3 text-right">
                <span className="flex items-center justify-end gap-1">
                  <History className="w-3 h-3 text-amber-600" /> Hist T1 (p50)
                </span>
              </th>
              <th className="py-3 px-3 text-right">Hist IQR</th>
              <th className="py-3 px-3 text-center">Samples</th>
              <th className="py-3 px-4 text-center">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono text-slate-700">
            {items.map((c: any, idx: number) => {
              const plantId = c.candidate_plant_id || c.plant_id;
              const plantCode = c.candidate_plant_code || c.plant_code || plantId;
              const plantName = c.candidate_plant_name || c.plant_name || plantCode;

              const isRec =
                Boolean(targetRecId) &&
                (c.is_recommended ||
                  c.is_winner ||
                  plantId === targetRecId ||
                  plantCode === targetRecId ||
                  c.recommended_plant_id === plantId ||
                  c.recommended_plant_code === plantCode);

              const isCurr =
                c.is_current_source ||
                c.is_current_plant ||
                plantId === currId ||
                plantCode === currId ||
                c.current_plant_id === plantId ||
                c.current_plant_code === currId;

              const crowFly = c.crow_fly_distance_km ?? c.crow_fly_km ?? 0;
              const gDist = c.google_candidate_distance_km ?? c.google_distance_km ?? null;
              const gDuration =
                c.google_candidate_duration_minutes ??
                c.google_duration_in_traffic_mins ??
                c.google_traffic_duration_minutes ??
                null;
              const gDelay =
                c.google_candidate_traffic_delay_minutes ??
                c.google_traffic_delay_mins ??
                c.google_traffic_delay_minutes ??
                0;
              const histP50 =
                c.historical_candidate_p50_minutes ??
                c.historical_t1_p50_mins ??
                c.erp_t1_p50_minutes ??
                null;
              const histIQR = c.historical_t1_iqr_mins ?? c.erp_t1_iqr_minutes ?? null;
              const sampleCount =
                c.historical_candidate_sample_count ??
                c.historical_sample_count ??
                c.erp_t1_sample_count ??
                0;
              const conf =
                c.historical_candidate_confidence ||
                c.historical_confidence ||
                (sampleCount >= 20 ? 'HIGH' : sampleCount >= 5 ? 'MEDIUM' : sampleCount > 0 ? 'LOW' : 'NONE');

              const isSelected = selectedCandidateId ? selectedCandidateId === plantId : (isRec || isCurr);
              const rowHighlight = isSelected
                ? isRec
                  ? 'bg-emerald-50/60 font-semibold ring-1 ring-emerald-300'
                  : isCurr
                  ? 'bg-blue-50/60 font-semibold ring-1 ring-blue-300'
                  : 'bg-amber-50/60 font-semibold ring-1 ring-amber-300'
                : 'hover:bg-slate-50/80 cursor-pointer';

              const confBadge =
                conf === 'HIGH'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : conf === 'MEDIUM'
                  ? 'bg-blue-50 text-blue-800 border-blue-200'
                  : conf === 'LOW'
                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                  : 'bg-slate-50 text-slate-600 border-slate-200';

              return (
                <tr
                  key={plantId || idx}
                  data-testid={`candidate-row-${plantCode || plantId || idx}`}
                  onClick={() => onSelectCandidate && plantId && onSelectCandidate(plantId)}
                  className={`transition-all cursor-pointer ${rowHighlight}`}
                >
                  {/* Plant Code & Name */}
                  <td className="py-3 px-4 font-semibold text-slate-900 font-sans">
                    <div className="flex items-center gap-1.5">
                      {isRec && <Star className="w-4 h-4 text-emerald-600 fill-emerald-500 shrink-0" />}
                      <div>
                        <div>{plantName}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{plantCode}</div>
                      </div>
                    </div>
                  </td>

                  {/* Role / Status */}
                  <td className="py-3 px-3 font-sans">
                    {isRec ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                        <Check className="w-3 h-3" /> Recommended Plant
                      </span>
                    ) : isCurr ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-800 border border-blue-200">
                        Current Plant
                      </span>
                    ) : (
                      <span className="text-slate-500 font-medium">Candidate</span>
                    )}
                  </td>

                  {/* Crow-Fly */}
                  <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600">
                    {crowFly ? `${crowFly.toFixed(1)} km` : '—'}
                  </td>

                  {/* Google Distance */}
                  <td className="py-3 px-3 text-right font-mono tabular-nums font-semibold text-slate-900">
                    {gDist !== null && gDist !== undefined ? `${gDist.toFixed(1)} km` : '—'}
                  </td>

                  {/* Traffic ETA */}
                  <td className="py-3 px-3 text-right font-mono tabular-nums font-bold text-slate-900">
                    {gDuration !== null && gDuration !== undefined ? (
                      `${gDuration.toFixed(1)}m`
                    ) : (
                      <span className="text-slate-400 text-xs italic font-sans">Unavailable</span>
                    )}
                  </td>

                  {/* Traffic Delay */}
                  <td className="py-3 px-3 text-right font-mono tabular-nums text-xs">
                    {gDelay > 0 ? (
                      <span className="text-amber-700 font-semibold bg-amber-50 px-1.5 py-0.5 rounded-md border border-amber-200/60">
                        +{gDelay.toFixed(1)}m
                      </span>
                    ) : (
                      <span className="text-slate-400">0.0m</span>
                    )}
                  </td>

                  {/* Historical T1 (p50) */}
                  <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600">
                    {histP50 !== null && histP50 !== undefined ? `${histP50.toFixed(1)}m` : '—'}
                  </td>

                  {/* Hist IQR */}
                  <td className="py-3 px-3 text-right font-mono tabular-nums text-slate-600">
                    {histIQR !== null && histIQR !== undefined ? `±${histIQR.toFixed(1)}m` : '—'}
                  </td>

                  {/* Sample Count */}
                  <td className="py-3 px-3 text-center font-mono tabular-nums text-slate-600">
                    {sampleCount}
                  </td>

                  {/* Confidence Badge */}
                  <td className="py-3 px-4 text-center font-sans">
                    <span className={`inline-block px-2 py-0.5 text-[10px] font-bold rounded-md border ${confBadge}`}>
                      {conf}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
