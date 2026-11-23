import React from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';

interface ReplayControlToolbarProps {
  isPlaying: boolean;
  onPlayToggle: () => void;
  onReset: () => void;
  playbackSpeed: number;
  onSpeedChange: (speed: number) => void;
  currentStepIndex: number;
  totalSteps: number;
  onStepChange: (index: number) => void;
  currentEventName: string | null;
  disabled?: boolean;
}

export const ReplayControlToolbar: React.FC<ReplayControlToolbarProps> = ({
  isPlaying,
  onPlayToggle,
  onReset,
  playbackSpeed,
  onSpeedChange,
  currentStepIndex,
  totalSteps,
  onStepChange,
  currentEventName,
  disabled = false,
}) => {
  const speeds = [1, 2, 4, 8, 16];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 mb-6 shadow-md flex flex-col md:flex-row items-center justify-between gap-4">
      {/* Controls: Play, Pause, Reset */}
      <div className="flex items-center space-x-3">
        <button
          onClick={onPlayToggle}
          disabled={disabled || totalSteps === 0}
          className={`flex items-center px-4 py-2 rounded-md font-medium text-sm transition-colors ${
            isPlaying
              ? 'bg-amber-600 hover:bg-amber-500 text-white'
              : 'bg-indigo-600 hover:bg-indigo-500 text-white'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          aria-label={isPlaying ? 'Pause Playback' : 'Play Timeline'}
        >
          {isPlaying ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <button
          onClick={onReset}
          disabled={disabled || totalSteps === 0}
          className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md transition-colors disabled:opacity-50"
          aria-label="Reset Playback"
          title="Reset to start"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Scrubber & Current Event */}
      <div className="flex-1 w-full max-w-xl mx-4">
        <div className="flex justify-between items-center text-xs text-slate-400 mb-1">
          <span className="font-semibold text-slate-200">
            Phase: <span className="text-indigo-400">{currentEventName || 'Initialized'}</span>
          </span>
          <span>
            Event {totalSteps > 0 ? currentStepIndex + 1 : 0} of {totalSteps}
          </span>
        </div>

        <input
          type="range"
          min={0}
          max={Math.max(0, totalSteps - 1)}
          value={currentStepIndex}
          onChange={(e) => onStepChange(parseInt(e.target.value, 10))}
          disabled={disabled || totalSteps === 0}
          className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500 disabled:opacity-50"
          aria-label="Timeline Scrubber"
        />
      </div>

      {/* Playback Speed Controls */}
      <div className="flex items-center space-x-1 bg-slate-800 p-1 rounded-md">
        <span className="text-xs text-slate-400 px-2 font-medium">Speed:</span>
        {speeds.map((speed) => (
          <button
            key={speed}
            onClick={() => onSpeedChange(speed)}
            disabled={disabled}
            className={`px-2 py-1 text-xs font-semibold rounded ${
              playbackSpeed === speed
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
            }`}
          >
            {speed}x
          </button>
        ))}
      </div>
    </div>
  );
};
