import { useState } from 'react';
import { Settings, Save, AlertTriangle, SlidersHorizontal } from 'lucide-react';
import type { SystemSettings } from '../lib/supabase';

interface SettingsPanelProps {
  settings: SystemSettings | null;
  onUpdate: (settings: Partial<SystemSettings>) => void;
}

export function SettingsPanel({ settings, onUpdate }: SettingsPanelProps) {
  const [local, setLocal] = useState<Partial<SystemSettings>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!settings) return null;

  const current = { ...settings, ...local };

  const handleChange = (key: keyof SystemSettings, value: unknown) => {
    setLocal((prev) => ({ ...prev, [key]: value }));
    setError(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onUpdate(local);
      setLocal({});
    } catch (e: any) {
      setError(e.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges = Object.keys(local).length > 0;

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-4 sm:p-5">
      <div className="flex items-center gap-2 mb-3 sm:mb-4">
        <SlidersHorizontal className="w-4 h-4 sm:w-5 sm:h-5 text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-200">Trading Settings</h3>
      </div>

      {error && (
        <div className="mb-3 sm:mb-4 p-2.5 sm:p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-red-400 shrink-0" />
          <span className="text-xs text-red-400">{error}</span>
        </div>
      )}

      <div className="space-y-3 sm:space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-[10px] sm:text-xs text-slate-400 mb-1">Base Amount ($)</label>
            <input
              type="number"
              min={0.35}
              max={10000}
              step={0.01}
              value={current.base_amount}
              onChange={(e) => handleChange('base_amount', parseFloat(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 sm:px-3 py-2 text-xs sm:text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-[10px] sm:text-xs text-slate-400 mb-1">Min Confidence (%)</label>
            <input
              type="number"
              min={50}
              max={100}
              value={current.min_confidence}
              onChange={(e) => handleChange('min_confidence', parseInt(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 sm:px-3 py-2 text-xs sm:text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-[10px] sm:text-xs text-slate-400 mb-1">Stop Loss ($)</label>
            <input
              type="number"
              min={0}
              value={current.stop_loss}
              onChange={(e) => handleChange('stop_loss', parseFloat(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 sm:px-3 py-2 text-xs sm:text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-[10px] sm:text-xs text-slate-400 mb-1">Take Profit ($)</label>
            <input
              type="number"
              min={0}
              value={current.take_profit}
              onChange={(e) => handleChange('take_profit', parseFloat(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 sm:px-3 py-2 text-xs sm:text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label className="block text-[10px] sm:text-xs text-slate-400 mb-1">Max Consecutive Losses</label>
            <input
              type="number"
              min={1}
              max={10}
              value={current.max_consecutive_losses}
              onChange={(e) => handleChange('max_consecutive_losses', parseInt(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 sm:px-3 py-2 text-xs sm:text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-[10px] sm:text-xs text-slate-400 mb-1">Max Trades/Hour</label>
            <input
              type="number"
              min={1}
              max={100}
              value={current.max_trades_per_hour}
              onChange={(e) => handleChange('max_trades_per_hour', parseInt(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 sm:px-3 py-2 text-xs sm:text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-2 sm:gap-3 pt-1 sm:pt-2">
          {[
            { key: 'enable_even_odd' as const, label: 'Even/Odd' },
            { key: 'enable_rise_fall' as const, label: 'Rise/Fall' },
            { key: 'enable_over_under' as const, label: 'Over/Under' },
            { key: 'enable_match_diff' as const, label: 'Match/Diff' },
            { key: 'enable_digit_analysis' as const, label: 'Digit Analysis' },
          ].map((toggle) => (
            <label key={toggle.key} className="flex items-center gap-1.5 sm:gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={current[toggle.key] as boolean}
                onChange={(e) => handleChange(toggle.key, e.target.checked)}
                className="w-3.5 h-3.5 sm:w-4 sm:h-4 rounded border-slate-600 bg-slate-900 text-blue-500 focus:ring-blue-500"
              />
              <span className="text-[10px] sm:text-xs text-slate-300">{toggle.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="mt-4 sm:mt-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 sm:gap-0">
        <label className="flex items-center gap-1.5 sm:gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={current.auto_trading}
            onChange={(e) => handleChange('auto_trading', e.target.checked)}
            className="w-3.5 h-3.5 sm:w-4 sm:h-4 rounded border-slate-600 bg-slate-900 text-blue-500 focus:ring-blue-500"
          />
          <span className="text-xs sm:text-sm text-slate-300">Auto Trading</span>
        </label>
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition-all ${
            hasChanges
              ? 'bg-blue-500 hover:bg-blue-600 text-white'
              : 'bg-slate-700 text-slate-500 cursor-not-allowed'
          }`}
        >
          <Save className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  );
}
