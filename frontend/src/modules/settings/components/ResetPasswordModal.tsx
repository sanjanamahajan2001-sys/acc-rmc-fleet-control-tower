import { env } from '../../../config/env';
import React, { useState } from 'react';
import { X, Copy, Check, AlertCircle } from 'lucide-react';
import { IconKeySecurity, IconCriticalAlert } from '../../../components/icons/LinealColorIcons';

interface ResetPasswordModalProps {
  isOpen: boolean;
  userId: string | null;
  username: string | null;
  onClose: () => void;
  onSuccess: () => void;
  token: string | null;
}

export const ResetPasswordModal: React.FC<ResetPasswordModalProps> = ({
  isOpen,
  userId,
  username,
  onClose,
  onSuccess,
  token,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!isOpen || !userId) return null;

  const handleReset = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(env.VITE_API_BASE_URL + '/users/' + userId + '/reset-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token,
        },
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.error?.message || result.detail || 'Failed to reset password');
      }

      setTempPassword(result.data.temporary_password);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Error resetting password');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (tempPassword) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(tempPassword);
      } else {
        const textarea = document.createElement('textarea');
        textarea.value = tempPassword;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleClose = () => {
    setTempPassword(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
      <div className="max-w-md w-full bg-white border border-slate-200/90 rounded-lg p-6 shadow-2xl space-y-4 relative text-slate-800">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2.5">
            <IconKeySecurity className="w-6 h-6 shrink-0" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">Reset User Password</h2>
              <p className="text-[11px] text-slate-500 font-medium">Invalidate active sessions &amp; generate temporary credential</p>
            </div>
          </div>
          <button onClick={handleClose} className="text-slate-400 hover:text-slate-600 p-1 rounded-md transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="p-2.5 rounded-md bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2 font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        {tempPassword ? (
          <div className="space-y-3.5 py-1 text-xs">
            <div className="p-3.5 rounded-md bg-amber-50 border border-amber-200 text-amber-800 space-y-1">
              <div className="flex items-center gap-2 font-bold text-amber-700">
                <IconCriticalAlert className="w-4 h-4" />
                <span>Password Reset Successfully!</span>
              </div>
              <p className="text-slate-600 text-xs">
                All active sessions for <strong>{username}</strong> have been invalidated. Provide this temporary credential to the user.
              </p>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
                New One-Time Temporary Password
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  readOnly
                  value={tempPassword}
                  className="flex-1 py-2 px-3 rounded-md bg-slate-50 border border-slate-200 font-mono text-xs text-amber-800 font-bold select-all focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleCopy}
                  className="py-2 px-3.5 rounded-md bg-blue-700 hover:bg-blue-800 text-white font-bold flex items-center gap-1.5 transition-colors shadow-xs"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
              </div>
            </div>

            <button
              onClick={handleClose}
              className="w-full py-2 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-bold transition-colors shadow-xs"
            >
              Done &amp; Close Dialog
            </button>
          </div>
        ) : (
          <div className="space-y-3.5 text-xs">
            <p className="text-slate-600">
              Are you sure you want to reset the password for user <strong className="text-slate-900">{username}</strong>?
            </p>
            <div className="p-3 rounded-md bg-slate-50 border border-slate-200 text-slate-600 text-[11px] space-y-1">
              <p>• Generating a new temporary password</p>
              <p>• Setting status to <code>PASSWORD_CHANGE_REQUIRED</code></p>
              <p>• Immediately invalidating all active user sessions (`token_version++`)</p>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={handleClose}
                className="py-1.5 px-3.5 rounded-md bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold transition-colors shadow-xs"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleReset}
                disabled={loading}
                className="py-1.5 px-4 rounded-md bg-blue-700 hover:bg-blue-800 text-white font-bold transition-colors disabled:opacity-50 shadow-xs"
              >
                {loading ? 'Resetting Password...' : 'Confirm Password Reset'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
