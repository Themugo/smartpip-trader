import { useState } from 'react';
import { Save, AlertTriangle, SlidersHorizontal, RefreshCw } from 'lucide-react';
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

  const inputFields = [
    { section: 'Risk Management', items: [
      { key: 'base_amount' as const, label: 'Base Amount', suffix: '$', min: 0.35, max: 10000, step: 0.01 },
      { key: 'stop_loss' as const, label: 'Stop Loss', suffix: '$', min: 0, max: 10000, step: 1 },
      { key: 'take_profit' as const, label: 'Take Profit', suffix: '$', min: 0, max: 10000, step: 1 },
    ]},
    { section: 'Trade Limits', items: [
      { key: 'min_confidence' as const, label: 'Min Confidence', suffix: '%', min: 50, max: 100, step: 1 },
      { key: 'max_consecutive_losses' as const, label: 'Max Consecutive Losses', suffix: '', min: 1, max: 10, step: 1 },
      { key: 'max_trades_per_hour' as const, label: 'Max Trades/Hour', suffix: '', min: 1, max: 100, step: 1 },
    ]},
  ];

  const toggles = [
    { key: 'auto_trading' as const, label: 'Auto Trading', description: 'Enable automated trade execution' },
    { key: 'enable_even_odd' as const, label: 'Even/Odd', description: 'Trade on digit parity' },
    { key: 'enable_rise_fall' as const, label: 'Rise/Fall', description: 'Trade on price direction' },
    { key: 'enable_over_under' as const, label: 'Over/Under', description: 'Trade on digit magnitude' },
    { key: 'enable_match_diff' as const, label: 'Match/Diff', description: 'Trade on digit matching' },
    { key: 'enable_digit_analysis' as const, label: 'Digit Analysis', description: 'Enable pattern recognition' },
  ];

  return (
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800/50 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <SlidersHorizontal className="w-4 h-4 text-white" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Settings</h3>
          <p className="text-[10px] text-slate-500">Configure trading parameters</p>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span className="text-xs text-red-400">{error}</span>
          </div>
        )}

        {/* Input Fields */}
        {inputFields.map((section) => (
          <div key={section.section} className="space-y-2">
            <h4 className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">{section.section}</h4>
            <div className="grid grid-cols-2 gap-2">
              {section.items.map((field) => (
                <div key={field.key}>
                  <label className="block text-[10px] text-slate-400 mb-1">{field.label}</label>
                  <div className="relative">
                    {field.suffix && (
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs">{field.suffix}</span>
                    )}
                    <input
                      type="number"
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={current[field.key] as number}
                      onChange={(e) => handleChange(field.key, parseFloat(e.target.value))}
                      className={`w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 font-mono ${field.suffix ? 'pl-6' : ''}`}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Toggles */}
        <div className="space-y-2">
          <h4 className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Features</h4>
          <div className="space-y-1.5">
            {toggles.map((toggle) => {
              const isEnabled = current[toggle.key] as boolean;
              return (
                <button
                  key={toggle.key}
                  onClick={() => handleChange(toggle.key, !isEnabled)}
                  className={`w-full flex items-center justify-between p-2.5 rounded-xl border transition-all ${
                    isEnabled
                      ? 'bg-emerald-500/5 border-emerald-500/20'
                      : 'bg-slate-800/30 border-slate-700/50'
                  }`}
                >
                  <div className="text-left">
                    <span className={`text-xs font-medium ${isEnabled ? 'text-emerald-400' : 'text-slate-300'}`}>
                      {toggle.label}
                    </span>
                    <p className="text-[10px] text-slate-500">{toggle.description}</p>
                  </div>
                  <div className={`w-9 h-5 rounded-full p-0.5 transition-all ${
                    isEnabled ? 'bg-emerald-500' : 'bg-slate-600'
                  }`}>
                    <div className={`w-4 h-4 rounded-full bg-white transition-all ${
                      isEnabled ? 'translate-x-4' : 'translate-x-0'
                    }`} />
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Save Button */}
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all ${
            hasChanges
              ? 'bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-400 hover:to-indigo-400 text-white shadow-lg shadow-blue-500/20'
              : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
          }`}
        >
          {saving ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4" />
              Save Changes
            </>
          )}
        </button>
      </div>
    </div>
  );
}
