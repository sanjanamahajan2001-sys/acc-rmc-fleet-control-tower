import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { env } from '../../../config/env';
import {
  RouteAnalysisSynthesisResult,
  RouteAnalysisSnapshotItem,
  RouteAnalysisExecutionRequest,
  RouteAnalysisBatchContext,
  TMIncidentAccessResult,
  TMIncidentAccessExecutionRequest,
  TMIncidentAccessResponse,
  OperationalPlantsListResponse,
  GoogleApiUsageResponse,
} from '../components/RouteAnalysis/routeAnalysis.types';

export interface UseRouteAnalysisHistoryParams {
  plant_id?: string;
  customer_id?: string;
  site_id?: string;
  recommendation_status?: string;
  evaluation_mode?: 'NOW' | 'PLANNED';
  limit?: number;
  page?: number;
  page_size?: number;
}

export const useRouteAnalysisBatchContext = () => {
  const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/batch-context`;

  return useQuery<{ success: boolean; data: RouteAnalysisBatchContext }>({
    queryKey: ['route-analysis-batch-context'],
    queryFn: async () => {
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch batch context: ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 30 * 1000,
  });
};

export const useRouteAnalysisHistory = (filters: UseRouteAnalysisHistoryParams = {}) => {
  const queryParams = new URLSearchParams();
  if (filters.plant_id && filters.plant_id !== 'ALL') queryParams.append('plant_id', filters.plant_id);
  if (filters.customer_id && filters.customer_id !== 'ALL') queryParams.append('customer_id', filters.customer_id);
  if (filters.site_id && filters.site_id !== 'ALL') queryParams.append('site_id', filters.site_id);
  if (filters.recommendation_status && filters.recommendation_status !== 'ALL') {
    queryParams.append('recommendation_status', filters.recommendation_status);
  }
  if (filters.evaluation_mode) {
    queryParams.append('evaluation_mode', filters.evaluation_mode);
  }
  if (filters.page) queryParams.append('page', String(filters.page));
  if (filters.page_size) {
    queryParams.append('page_size', String(filters.page_size));
  } else if (filters.limit) {
    queryParams.append('page_size', String(filters.limit));
  }

  const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/history?${queryParams.toString()}`;

  return useQuery<{
    success: boolean;
    data: RouteAnalysisSnapshotItem[];
    total_count: number;
    page: number;
    page_size: number;
    total_pages: number;
  }>({
    queryKey: ['route-analysis-history', filters],
    queryFn: async () => {
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch route analysis history: ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 60 * 1000,
  });
};

export const useRouteAnalysisSnapshot = (analysisId: string | null) => {
  const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/snapshot/${analysisId}`;

  return useQuery<{ success: boolean; data: RouteAnalysisSynthesisResult }>({
    queryKey: ['route-analysis-snapshot', analysisId],
    queryFn: async () => {
      if (!analysisId) throw new Error('No analysis ID provided');
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch route analysis snapshot: ${response.statusText}`);
      }
      return response.json();
    },
    enabled: !!analysisId,
    staleTime: 300 * 1000,
  });
};

export const useExecuteRouteAnalysis = () => {
  const queryClient = useQueryClient();

  return useMutation<{ success: boolean; data: RouteAnalysisSynthesisResult }, Error, RouteAnalysisExecutionRequest>({
    mutationFn: async (payload: RouteAnalysisExecutionRequest) => {
      const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis`;
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody.detail || `Route analysis execution failed: ${response.statusText}`);
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['route-analysis-history'] });
      queryClient.invalidateQueries({ queryKey: ['route-analysis-batch-context'] });
    },
  });
};

export const useGenerateRouteAnalysisBatch = () => {
  const queryClient = useQueryClient();

  return useMutation<
    { success: boolean; batch_id: string | null; generated_count: number; message: string },
    Error,
    { force_refresh?: boolean; analysis_mode?: string; planned_departure_time?: string } | void
  >({
    mutationFn: async (params) => {
      const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/generate-batch`;
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(params || {}),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody.detail || `Route analysis batch generation failed: ${response.statusText}`);
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['route-analysis-history'] });
      queryClient.invalidateQueries({ queryKey: ['route-analysis-batch-context'] });
    },
  });
};

// ============================================================
// TM INCIDENT / STUCK TM CURRENT-TRAFFIC DECISION SUPPORT HOOKS
// ============================================================

export const useOperationalPlants = () => {
  const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/tm-incident-access/plants`;

  return useQuery<OperationalPlantsListResponse>({
    queryKey: ['operational-plants-incident-access'],
    queryFn: async () => {
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch operational plants: ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000,
  });
};

export const useExecuteTMIncidentAccess = () => {
  return useMutation<TMIncidentAccessResponse, Error, TMIncidentAccessExecutionRequest>({
    mutationFn: async (payload: TMIncidentAccessExecutionRequest) => {
      const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/tm-incident-access`;
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({}));
        throw new Error(errBody.detail || `TM incident access analysis failed: ${response.statusText}`);
      }

      return response.json();
    },
  });
};

export const useTMIncidentAccessSnapshot = (analysisId: string | null) => {
  const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/tm-incident-access/${analysisId}`;

  return useQuery<TMIncidentAccessResponse>({
    queryKey: ['tm-incident-access-snapshot', analysisId],
    queryFn: async () => {
      if (!analysisId) throw new Error('No analysis ID provided');
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch TM incident access snapshot: ${response.statusText}`);
      }
      return response.json();
    },
    enabled: !!analysisId,
    staleTime: 300 * 1000,
  });
};

export const useGoogleApiUsage = () => {
  const url = `${env.VITE_API_BASE_URL}/dispatch-analysis/route-analysis/api-usage`;

  return useQuery<GoogleApiUsageResponse>({
    queryKey: ['google-api-usage'],
    queryFn: async () => {
      const token =
        localStorage.getItem('fct_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('access_token');
      const response = await fetch(url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch Google API usage: ${response.statusText}`);
      }
      return response.json();
    },
    staleTime: 30 * 1000,
  });
};

