import { env } from '../../../config/env';
/**
 * WS-08.4 Timeline Replay API Service Client.
 * Consumes production WS-08.3 REST endpoints (${env.VITE_API_BASE_URL}/timeline-replay/dispatches).
 */

export interface DispatchReplayListItem {
  dispatch_id: string;
  dispatch_number: string;
  plant_id: string;
  customer_id: string;
  vehicle_id: string | null;
  dispatch_date: string;
  status: string;
  has_telemetry: boolean;
}

export interface DispatchReplayListResponse {
  items: DispatchReplayListItem[];
  total_count: number;
  page: number;
  page_size: number;
}

export type EventAuthorityType = 'DIRECT' | 'DERIVED' | 'INFERRED' | 'UNAVAILABLE';
export type SpatialModeType = 'GPS_TRAJECTORY' | 'LOCATION_CONTEXT_ONLY' | 'NO_SPATIAL_DATA';
export type DurationCompletenessType = 'COMPLETE' | 'PARTIAL' | 'UNAVAILABLE';

export interface TrajectoryPoint {
  latitude: number;
  longitude: number;
  timestamp: string | null;
  speed_kmh: number | null;
  heading_deg: number | null;
}

export interface TimelineEventItem {
  event_type: string;
  authority_type: EventAuthorityType;
  timestamp: string | null;
  duration_mins: number | null;
  location_name: string | null;
  is_inferred_estimate: boolean;
  notes: string | null;
}

export interface TelemetrySummary {
  avg_speed_kmh: number | null;
  max_speed_kmh: number | null;
  drum_rotation_rpm: number | null;
  telemetry_matched: boolean;
}

export interface SpatialContext {
  has_gps_breadcrumbs: boolean;
  spatial_mode: SpatialModeType;
  plant_latitude: number | null;
  plant_longitude: number | null;
  site_latitude: number | null;
  site_longitude: number | null;
  trajectory_points: TrajectoryPoint[];
}

export interface DurationCompleteness {
  total_trip_duration_mins: number | null;
  duration_completeness: DurationCompletenessType;
  missing_segments: string[];
}

export interface DispatchTimelineReplayDetail {
  dispatch_id: string;
  dispatch_number: string;
  plant_id: string;
  customer_id: string;
  vehicle_id: string | null;
  dataset_id: string | null;
  status: string;
  duration_summary: DurationCompleteness;
  t2c_retention_mins: number | null;
  lifecycle_events: TimelineEventItem[];
  telemetry_summary: TelemetrySummary;
  spatial_context: SpatialContext;
  correlated_alert_count: number;
}

export interface TimelineReplayQueryFilter {
  plant_id?: string;
  customer_id?: string;
  dataset_id?: string;
  page?: number;
  page_size?: number;
}

export const fetchTimelineReplayDispatches = async (
  filters: TimelineReplayQueryFilter
): Promise<DispatchReplayListResponse> => {
  const params = new URLSearchParams();
  if (filters.plant_id) params.append('plant_id', filters.plant_id);
  if (filters.customer_id) params.append('customer_id', filters.customer_id);
  if (filters.dataset_id) params.append('dataset_id', filters.dataset_id);
  params.append('page', (filters.page || 1).toString());
  params.append('page_size', (filters.page_size || 50).toString());

  const response = await fetch(env.VITE_API_BASE_URL + '/timeline-replay/dispatches?' + params.toString(), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch timeline replay dispatches (HTTP ' + response.status + ')');
  }

  return response.json();
};

export const fetchDispatchTimelineDetail = async (
  dispatchId: string,
  filters?: TimelineReplayQueryFilter
): Promise<DispatchTimelineReplayDetail> => {
  const params = new URLSearchParams();
  if (filters?.plant_id) params.append('plant_id', filters.plant_id);
  if (filters?.customer_id) params.append('customer_id', filters.customer_id);
  if (filters?.dataset_id) params.append('dataset_id', filters.dataset_id);

  const response = await fetch(env.VITE_API_BASE_URL + '/timeline-replay/dispatches/' + dispatchId + '?' + params.toString(), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Dispatch '" + dispatchId + "' not found under active operational scope.");
    }
    throw new Error('Failed to fetch dispatch timeline detail (HTTP ' + response.status + ')');
  }

  return response.json();
};
