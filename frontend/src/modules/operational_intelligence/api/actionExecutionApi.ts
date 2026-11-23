import { apiClient } from '../../../api/client';

export interface ActionLogItem {
  action_id: string;
  recommendation_id: string;
  prediction_snapshot_id: string;
  model_family: string;
  model_version: string;
  dataset_id: string | null;
  operation_date: string;
  plant_code: string;
  customer_code: string;
  dispatch_id: string;
  dispatch_code: string | null;
  action_type: string;
  action_parameters: Record<string, any> | null;
  predicted_risk_exposure_inr: number | null;
  estimated_avoided_exposure_inr: number | null;
  actual_avoided_loss_inr: number | null;
  action_status: 'PENDING' | 'ACCEPTED' | 'IN_PROGRESS' | 'EXECUTED' | 'REJECTED' | 'DEFERRED' | 'FAILED';
  dispatcher_id: string | null;
  dispatcher_role: string | null;
  dispatcher_notes: string | null;
  reason_code: string | null;
  decision_timestamp: string | null;
  accepted_at: string | null;
  started_at: string | null;
  execution_confirmed_at: string | null;
  rejected_at: string | null;
  deferred_at: string | null;
  version_lock: number;
  idempotency_key: string;
}

export interface ActionQueueResponse {
  total_count: number;
  items: ActionLogItem[];
  filter_scope: {
    plant_id: string;
    customer_id: string;
    dataset_type: string;
  };
}

export interface ActionOperationResponse {
  success: boolean;
  message: string;
  action: ActionLogItem;
  is_idempotent_replay: boolean;
}

export const actionExecutionApi = {
  generateActions: async (): Promise<{ success: boolean; message: string }> => {
    const res = await apiClient.post<{ success: boolean; message: string }>('/operational-intelligence/actions/generate', {}, { timeout: 120000 });
    return res.data;
  },

  getActionQueue: async (params: {
    plant_id?: string;
    customer_id?: string;
    dataset_type?: string;
    action_status?: string;
    action_type?: string;
  }): Promise<ActionQueueResponse> => {
    const res = await apiClient.get<ActionQueueResponse>('/operational-intelligence/actions', { params });
    return res.data;
  },

  acceptRecommendation: async (
    actionId: string,
    payload: {
      dispatcher_id: string;
      dispatcher_role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN';
      idempotency_key: string;
      version_lock: number;
      notes?: string;
    }
  ): Promise<ActionOperationResponse> => {
    const res = await apiClient.post<ActionOperationResponse>(
      '/operational-intelligence/actions/' + actionId + '/accept',
      payload
    );
    return res.data;
  },

  startProgress: async (
    actionId: string,
    payload: {
      dispatcher_id: string;
      dispatcher_role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN';
      idempotency_key: string;
      version_lock: number;
      notes?: string;
    }
  ): Promise<ActionOperationResponse> => {
    const res = await apiClient.post<ActionOperationResponse>(
      '/operational-intelligence/actions/' + actionId + '/start',
      payload
    );
    return res.data;
  },

  confirmExecution: async (
    actionId: string,
    payload: {
      dispatcher_id: string;
      dispatcher_role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN';
      idempotency_key: string;
      version_lock: number;
      notes?: string;
    }
  ): Promise<ActionOperationResponse> => {
    const res = await apiClient.post<ActionOperationResponse>(
      '/operational-intelligence/actions/' + actionId + '/confirm-execution',
      payload
    );
    return res.data;
  },

  rejectRecommendation: async (
    actionId: string,
    payload: {
      dispatcher_id: string;
      dispatcher_role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN';
      idempotency_key: string;
      version_lock: number;
      reason_code: string;
      notes?: string;
    }
  ): Promise<ActionOperationResponse> => {
    const res = await apiClient.post<ActionOperationResponse>(
      '/operational-intelligence/actions/' + actionId + '/reject',
      payload
    );
    return res.data;
  },

  deferRecommendation: async (
    actionId: string,
    payload: {
      dispatcher_id: string;
      dispatcher_role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN';
      idempotency_key: string;
      version_lock: number;
      reason_code: string;
      retry_at?: string;
      notes?: string;
    }
  ): Promise<ActionOperationResponse> => {
    const res = await apiClient.post<ActionOperationResponse>(
      '/operational-intelligence/actions/' + actionId + '/defer',
      payload
    );
    return res.data;
  },
};
