import React, { useState } from 'react';
import { X, CheckCircle2, AlertTriangle, ShieldAlert, FileText } from 'lucide-react';
import { ActionLogItem } from '../api/actionExecutionApi';

interface ModalProps {
  action: ActionLogItem | null;
  isOpen: boolean;
  onClose: () => void;
}

interface AcceptModalProps extends ModalProps {
  onConfirm: (notes: string, role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN') => void;
  isSubmitting: boolean;
}

export const AcceptActionModal: React.FC<AcceptModalProps> = ({
  action,
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
}) => {
  const [notes, setNotes] = useState('');
  const [role, setRole] = useState<'DISPATCHER' | 'SUPERVISOR' | 'ADMIN'>('DISPATCHER');

  if (!isOpen || !action) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="border border-slate-200/90 rounded-lg max-w-lg w-full p-6 shadow-xl bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <h3 className="text-base font-bold flex items-center gap-2 text-slate-900">
            <CheckCircle2 className="w-5 h-5 text-blue-700" />
            Approve Operational Recommendation Intent
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-md text-slate-500">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 text-xs mb-5">
          <div className="border border-blue-200 bg-blue-50/70 p-3 rounded-md font-medium text-blue-900">
            <strong className="text-slate-900">State Transition:</strong> PENDING ➔ ACCEPTED (Intent Approved).
            <p className="mt-1 font-medium text-slate-600">
              Approving intent confirms your plan to perform the operational action. It does NOT mark physical completion.
            </p>
          </div>

          <div className="p-3 rounded-md space-y-1.5 font-mono border border-slate-200 bg-slate-50 font-medium text-slate-900">
            <div><span className="text-slate-500">Action ID:</span> {action.action_id}</div>
            <div><span className="text-slate-500">Dispatch ID:</span> {action.dispatch_code || action.dispatch_id}</div>
            <div><span className="text-slate-500">Plant Code:</span> {action.plant_code}</div>
            <div><span className="text-slate-500">Predicted Risk:</span> ₹{action.predicted_risk_exposure_inr}</div>
            <div><span className="text-slate-500">Est. Avoided Exposure:</span> ₹{action.estimated_avoided_exposure_inr || (action.predicted_risk_exposure_inr ? action.predicted_risk_exposure_inr * 0.85 : 0)}</div>
          </div>

          <div>
            <label className="block font-bold mb-1 text-slate-800">Dispatcher Role:</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as any)}
              className="w-full border border-slate-200 rounded-md p-2 font-bold bg-white text-slate-800 focus:border-blue-600 focus:outline-hidden"
            >
              <option value="DISPATCHER">DISPATCHER — Standard Operations</option>
              <option value="SUPERVISOR">SUPERVISOR — Operational Supervisor Override</option>
              <option value="ADMIN">ADMIN — Executive Administrator</option>
            </select>
          </div>

          <div>
            <label className="block font-bold mb-1 text-slate-800">Dispatcher Notes (Optional):</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add operational context, truck driver instructions, or plant notes..."
              className="w-full border border-slate-200 rounded-md p-2 h-20 font-medium bg-white text-slate-800 focus:border-blue-600 focus:outline-hidden"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button onClick={onClose} disabled={isSubmitting} className="px-4 py-2 text-xs font-bold rounded-md border border-slate-200 hover:bg-slate-50 bg-white text-slate-700">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(notes, role)}
            disabled={isSubmitting}
            className="px-4 py-2 text-white text-xs font-bold rounded-md flex items-center gap-1.5 shadow-xs bg-blue-700 hover:bg-blue-800 transition"
          >
            {isSubmitting ? 'Approving...' : 'Confirm Intent Approval'}
          </button>
        </div>
      </div>
    </div>
  );
};

interface ConfirmExecutionModalProps extends ModalProps {
  onConfirm: (notes: string, role: 'DISPATCHER' | 'SUPERVISOR' | 'ADMIN') => void;
  isSubmitting: boolean;
}

export const ConfirmExecutionModal: React.FC<ConfirmExecutionModalProps> = ({
  action,
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
}) => {
  const [notes, setNotes] = useState('');
  const [role, setRole] = useState<'DISPATCHER' | 'SUPERVISOR' | 'ADMIN'>('DISPATCHER');

  if (!isOpen || !action) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="border border-slate-200/90 rounded-lg max-w-lg w-full p-6 shadow-xl bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <h3 className="text-base font-bold flex items-center gap-2 text-slate-900">
            <CheckCircle2 className="w-5 h-5 text-emerald-700" />
            Explicit Physical Execution Confirmation
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-md text-slate-500">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 text-xs mb-5">
          <div className="border border-emerald-200 bg-emerald-50/70 p-3 rounded-md font-medium text-emerald-900">
            <strong className="text-slate-900">Explicit Human Confirmation Required:</strong>
            <p className="mt-1 font-medium text-slate-600">
              Confirm that you physically verified or executed this operational offset at the plant/truck level. Zero automatic ERP write-back is performed.
            </p>
          </div>

          <div className="p-3 rounded-md space-y-1.5 font-mono border border-slate-200 bg-slate-50 font-medium text-slate-900">
            <div><span className="text-slate-500">Action ID:</span> {action.action_id}</div>
            <div><span className="text-slate-500">Current Status:</span> {action.action_status}</div>
            <div><span className="text-slate-500">Target State:</span> EXECUTED</div>
            <div><span className="text-slate-500">Plant Code:</span> {action.plant_code}</div>
          </div>

          <div>
            <label className="block font-bold mb-1 text-slate-800">Dispatcher Role:</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as any)}
              className="w-full border border-slate-200 rounded-md p-2 font-bold bg-white text-slate-800 focus:border-blue-600 focus:outline-hidden"
            >
              <option value="DISPATCHER">DISPATCHER — Standard Operations</option>
              <option value="SUPERVISOR">SUPERVISOR — Operational Supervisor Override</option>
              <option value="ADMIN">ADMIN — Executive Administrator</option>
            </select>
          </div>

          <div>
            <label className="block font-bold mb-1 text-slate-800">Execution Verification Notes:</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Verified truck gate arrival offset at plant bay 2..."
              className="w-full border border-slate-200 rounded-md p-2 h-20 font-medium bg-white text-slate-800 focus:border-blue-600 focus:outline-hidden"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button onClick={onClose} disabled={isSubmitting} className="px-4 py-2 text-xs font-bold rounded-md border border-slate-200 hover:bg-slate-50 bg-white text-slate-700">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(notes, role)}
            disabled={isSubmitting}
            className="px-4 py-2 text-white text-xs font-bold rounded-md flex items-center gap-1.5 shadow-xs bg-emerald-700 hover:bg-emerald-800 transition"
          >
            {isSubmitting ? 'Confirming...' : 'Confirm Physical Execution'}
          </button>
        </div>
      </div>
    </div>
  );
};

interface RejectDeferModalProps extends ModalProps {
  mode: 'REJECT' | 'DEFER';
  onConfirm: (reasonCode: string, notes: string, retryAt?: string) => void;
  isSubmitting: boolean;
}

export const RejectDeferModal: React.FC<RejectDeferModalProps> = ({
  action,
  isOpen,
  mode,
  onClose,
  onConfirm,
  isSubmitting,
}) => {
  const [reasonCode, setReasonCode] = useState('SITE_ACCESS_RESTRICTION');
  const [notes, setNotes] = useState('');
  const [retryAt, setRetryAt] = useState('');

  if (!isOpen || !action) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="border border-slate-200/90 rounded-lg max-w-lg w-full p-6 shadow-xl bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <h3 className="text-base font-bold flex items-center gap-2 text-slate-900">
            {mode === 'REJECT' ? <ShieldAlert className="w-5 h-5 text-rose-700" /> : <AlertTriangle className="w-5 h-5 text-slate-600" />}
            {mode === 'REJECT' ? 'Reject Recommendation' : 'Defer Action Recommendation'}
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-md text-slate-500">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 text-xs mb-5">
          <div>
            <label className="block font-bold mb-1 text-slate-800">Authoritative Reason Code:</label>
            <select
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value)}
              className="w-full border border-slate-200 rounded-md p-2 font-bold bg-white text-slate-800 focus:border-blue-600 focus:outline-hidden"
            >
              <option value="SITE_ACCESS_RESTRICTION">SITE_ACCESS_RESTRICTION — Customer site unavailable</option>
              <option value="MIXER_CAPACITY_LIMIT">MIXER_CAPACITY_LIMIT — Plant batch capacity full</option>
              <option value="TRAFFIC_ROAD_BLOCKAGE">TRAFFIC_ROAD_BLOCKAGE — Transit corridor congestion</option>
              <option value="WEATHER_DISRUPTION">WEATHER_DISRUPTION — Heavy rainfall or site mudding</option>
              <option value="SUPERVISOR_OVERRIDE">SUPERVISOR_OVERRIDE — Operational priority shift</option>
            </select>
          </div>

          {mode === 'DEFER' && (
            <div>
              <label className="block font-bold mb-1 text-slate-800">Retry Timestamp (Optional):</label>
              <input
                type="datetime-local"
                value={retryAt}
                onChange={(e) => setRetryAt(e.target.value)}
                className="w-full border border-slate-200 rounded-md p-2 font-medium bg-white text-slate-800 focus:border-blue-600 focus:outline-hidden"
              />
            </div>
          )}

          <div>
            <label className="block font-bold mb-1 text-slate-800">Dispatcher Audit Notes:</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Required operational justification for audit lineage..."
              className="w-full border border-slate-200 rounded-md p-2 h-20 font-medium bg-white text-slate-800 focus:border-blue-600 focus:outline-hidden"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button onClick={onClose} disabled={isSubmitting} className="px-4 py-2 text-xs font-bold rounded-md border border-slate-200 hover:bg-slate-50 bg-white text-slate-700">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reasonCode, notes, retryAt)}
            disabled={isSubmitting}
            className={`px-4 py-2 text-white text-xs font-bold rounded-md flex items-center gap-1.5 shadow-xs transition ${
              mode === 'REJECT' ? 'bg-rose-700 hover:bg-rose-800' : 'bg-slate-700 hover:bg-slate-800'
            }`}
          >
            {isSubmitting ? 'Submitting...' : mode === 'REJECT' ? 'Confirm Rejection' : 'Confirm Deferral'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const ActionAuditModal: React.FC<ModalProps> = ({ action, isOpen, onClose }) => {
  if (!isOpen || !action) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="border border-slate-200/90 rounded-lg max-w-2xl w-full p-6 shadow-xl max-h-[90vh] overflow-y-auto z-[10000] bg-white">
        <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
          <h3 className="text-base font-bold flex items-center gap-2 text-slate-900">
            <FileText className="w-5 h-5 text-blue-700" />
            End-to-End Decision &amp; Lineage Traceability Audit
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-md text-slate-500">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4 text-xs font-mono text-slate-900">
          <div className="p-4 rounded-md space-y-2 border border-slate-200 bg-slate-50">
            <div className="font-bold uppercase text-[11px] mb-1 text-blue-700">1. Action &amp; Recommendation Identity</div>
            <div><span className="text-slate-500">Action ID:</span> {action.action_id}</div>
            <div><span className="text-slate-500">Recommendation ID:</span> {action.recommendation_id}</div>
            <div><span className="text-slate-500">Dispatch ID:</span> {action.dispatch_code || action.dispatch_id}</div>
            <div><span className="text-slate-500">Plant Code:</span> {action.plant_code}</div>
            <div><span className="text-slate-500">Customer Code:</span> {action.customer_code}</div>
            <div><span className="text-slate-500">Action Type:</span> {action.action_type}</div>
          </div>

          <div className="p-4 rounded-md space-y-2 border border-slate-200 bg-slate-50">
            <div className="font-bold uppercase text-[11px] mb-1 text-blue-700">2. Phase 6 Prediction Lineage</div>
            <div><span className="text-slate-500">Snapshot ID:</span> {action.prediction_snapshot_id}</div>
            <div><span className="text-slate-500">Model Family:</span> {action.model_family}</div>
            <div><span className="text-slate-500">Model Version:</span> {action.model_version}</div>
            <div><span className="text-slate-500">Dataset ID:</span> {action.dataset_id || 'DS-20260805-001'}</div>
          </div>

          <div className="p-4 rounded-md space-y-2 border border-slate-200 bg-slate-50">
            <div className="font-bold uppercase text-[11px] mb-1 text-blue-700">3. Financial Lineage Governance</div>
            <div><span className="text-slate-500">Governed Rate Lineage:</span> RATE_SPECIFICATION_GLOBAL_V1 (₹25/min queue holding)</div>
            <div>
              <span className="text-slate-500">Predicted Risk Exposure:</span>{' '}
              <strong className="text-amber-700">
                {action.predicted_risk_exposure_inr !== null && action.predicted_risk_exposure_inr !== undefined
                  ? `₹${Math.round(action.predicted_risk_exposure_inr).toLocaleString('en-IN')}`
                  : '₹0 (Nominal SLA Protection Buffer)'}
              </strong>
            </div>
            <div>
              <span className="text-slate-500">Estimated Avoided Exposure:</span>{' '}
              <strong className="text-emerald-700">
                {action.estimated_avoided_exposure_inr !== null && action.estimated_avoided_exposure_inr !== undefined
                  ? `₹${Math.round(action.estimated_avoided_exposure_inr).toLocaleString('en-IN')}`
                  : action.predicted_risk_exposure_inr !== null && action.predicted_risk_exposure_inr !== undefined
                  ? `₹${Math.round(action.predicted_risk_exposure_inr).toLocaleString('en-IN')} (Targeted Protection)`
                  : 'SLA Buffer (Post-Trip Audited)'}
              </strong>
            </div>
            <div>
              <span className="text-slate-500">Actual Avoided Loss (Post-Trip):</span>{' '}
              {action.actual_avoided_loss_inr !== null ? `₹${action.actual_avoided_loss_inr.toLocaleString('en-IN')}` : 'Pending Outcome Reconciliation'}
            </div>
          </div>

          <div className="p-4 rounded-md space-y-2 border border-slate-200 bg-slate-50">
            <div className="font-bold uppercase text-[11px] mb-1 text-blue-700">4. Dispatcher Audit &amp; State Audit</div>
            <div><span className="text-slate-500">Current Status:</span> {action.action_status}</div>
            <div><span className="text-slate-500">Dispatcher ID:</span> {action.dispatcher_id || 'N/A'}</div>
            <div><span className="text-slate-500">Dispatcher Role:</span> {action.dispatcher_role || 'N/A'}</div>
            <div><span className="text-slate-500">Accepted Timestamp:</span> {action.accepted_at || 'N/A'}</div>
            <div><span className="text-slate-500">Started Timestamp:</span> {action.started_at || 'N/A'}</div>
            <div><span className="text-slate-500">Execution Confirmed:</span> {action.execution_confirmed_at || 'N/A'}</div>
            <div><span className="text-slate-500">Idempotency Key:</span> {action.idempotency_key}</div>
            <div><span className="text-slate-500">Version Lock:</span> {action.version_lock}</div>
          </div>
        </div>

        <div className="flex items-center justify-end pt-4 border-t border-slate-100 mt-4">
          <button onClick={onClose} className="px-4 py-2 text-xs font-bold rounded-md border border-slate-200 hover:bg-slate-50 bg-white text-slate-700">
            Close Lineage Trace
          </button>
        </div>
      </div>
    </div>
  );
};
