import { usePermissions } from '../../../hooks/usePermissions';
import React, { useRef, useState } from 'react';
import { AlertCircle, RefreshCw, XCircle } from 'lucide-react';
import { IconCalendarCheckmark } from '../../../components/icons/LinealColorIcons';
import { IconCloudUpload } from '../../../components/icons/LinealColorIcons';
import { useERPUploadStore, useERPNotificationStore, useERPProgressStore, useERPJobsStore, useERPStatisticsStore } from '../stores';

export const UploadZone: React.FC = () => {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { uploading, uploadFile, error, activeJob, resetUpload } = useERPUploadStore();
  const addNotification = useERPNotificationStore((s) => s.addNotification);
  const connectSSE = useERPProgressStore((s) => s.connectSSE);
  const { canEdit } = usePermissions();
  const hasEditPermission = canEdit('erp_import');

  const handleFiles = async (files: FileList | null) => {
    if (!hasEditPermission) {
      addNotification('error', 'Action restricted: View-only permissions on ERP Import.');
      return;
    }
    if (!files || files.length === 0) return;
    const file = files[0];

    // File validation
    const validExtensions = ['.xlsx', '.xlsm', '.xls', '.csv'];
    const hasValidExt = validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!hasValidExt) {
      addNotification('error', 'Invalid file type. Accepted formats: ' + validExtensions.join(', '));
      return;
    }

    if (file.size > 524288000) { // 500 MB
      addNotification('error', 'File size exceeds maximum limit of 500MB');
      return;
    }

    const job = await uploadFile(file);
    if (job) {
      addNotification('success', 'Workbook "' + file.name + '" uploaded successfully. Job ID: ' + job.job_number);
      connectSSE(job.job_number);
      useERPJobsStore.getState().fetchJobs();
      useERPStatisticsStore.getState().fetchStatistics();
      useERPStatisticsStore.getState().fetchAuditLogs();
    } else {
      addNotification('error', 'Workbook upload failed.');
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div
      aria-label="Workbook Upload Zone"
      tabIndex={0}
      onDragEnter={handleDrag}
      onDragOver={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
      className={`relative p-6 rounded-lg border-2 border-dashed transition-all duration-200 shadow-xs bg-white ${
        dragActive ? 'border-blue-600 bg-blue-50/40' : 'border-slate-200/90 hover:border-slate-300'
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xlsm,.xls,.csv"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className="flex flex-col items-center justify-center text-center space-y-3">
        <IconCloudUpload className="w-10 h-10" />

        <div>
          <h3 className="text-base font-bold text-slate-900">
            Upload ERP Workbook
          </h3>
          <p className="text-xs font-medium text-slate-600 mt-0.5">
            Drag &amp; drop your Excel or CSV file here, or{' '}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="font-bold underline text-blue-700 hover:text-blue-800"
            >
              browse
            </button>
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono font-medium text-slate-500">
          <span>Supported: .xlsx, .xlsm, .xls, .csv</span>
          <span>•</span>
          <span>Max Size: 500MB</span>
          <span>•</span>
          <span>SHA-256 Verified</span>
        </div>

        {uploading && (
          <div className="flex items-center gap-2 text-xs font-bold text-blue-700 bg-blue-50 px-3 py-1.5 rounded-md border border-blue-200">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            Uploading &amp; verifying checksum...
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 p-2.5 rounded-md border text-xs font-bold bg-rose-50 border-rose-200 text-rose-700">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {activeJob && (
          <div className="flex items-center justify-between w-full p-2.5 rounded-md border text-xs font-bold bg-emerald-50 border-emerald-200 text-emerald-800">
            <div className="flex items-center gap-2">
              <IconCalendarCheckmark className="w-4 h-4 shrink-0" />
              <span>Job Created: {activeJob.job_number} ({activeJob.file_name})</span>
            </div>
            <button
              type="button"
              onClick={resetUpload}
              className="p-1 hover:bg-emerald-100 rounded text-emerald-800 transition-colors"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
