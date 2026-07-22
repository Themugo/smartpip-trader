import { useState } from 'react';
import { Key, Link2, LogIn, Shield, Eye, EyeOff } from 'lucide-react';

interface BrokerConnectPanelProps {
  isAuthenticated: boolean;
  userToken: string;
  hasTradingToken: boolean;
  onSaveToken: (token: string) => void;
  onSignIn: () => void;
}

export function BrokerConnectPanel({
  isAuthenticated,
  userToken,
  hasTradingToken,
  onSaveToken,
  onSignIn,
}: BrokerConnectPanelProps) {
  const [tokenInput, setTokenInput] = useState(userToken);
  const [showToken, setShowToken] = useState(false);
  const [saved, setSaved] = useState(false);

  if (!isAuthenticated) {
    return (
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl border border-slate-700 p-4 sm:p-5">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-emerald-500/20 rounded-lg flex items-center justify-center">
            <Link2 className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="font-medium text-white">Live Trading</p>
            <p className="text-xs text-slate-400">Sign in to connect your Deriv account</p>
          </div>
        </div>
        <p className="text-xs text-slate-400 mb-3">
          Market data is free and public. Create an account only when you are ready to place live trades.
        </p>
        <button
          onClick={onSignIn}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium text-sm transition-colors"
        >
          <LogIn className="w-4 h-4" />
          Sign In to Trade
        </button>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl border border-slate-700 p-4 sm:p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${hasTradingToken ? 'bg-emerald-500/20' : 'bg-amber-500/20'}`}>
          <Key className={`w-5 h-5 ${hasTradingToken ? 'text-emerald-400' : 'text-amber-400'}`} />
        </div>
        <div>
          <p className="font-medium text-white">Deriv API Token</p>
          <p className="text-xs text-slate-400">
            {hasTradingToken ? 'Connected for live trading' : 'Add your token to trade live'}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <label className="block text-[10px] text-slate-400">Your Deriv API token</label>
        <div className="relative">
          <input
            type={showToken ? 'text' : 'password'}
            value={tokenInput}
            onChange={(e) => {
              setTokenInput(e.target.value);
              setSaved(false);
            }}
            placeholder="Paste token from Deriv account settings"
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 pr-10 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={() => setShowToken(!showToken)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        <button
          onClick={() => {
            onSaveToken(tokenInput);
            setSaved(true);
          }}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Save Token
        </button>
        {saved && (
          <p className="text-xs text-emerald-400 flex items-center gap-1">
            <Shield className="w-3 h-3" /> Token saved locally on this device
          </p>
        )}
        <p className="text-[10px] text-slate-500">
          Get your token from Deriv → Account settings → API token. Required only for live trade execution.
        </p>
      </div>
    </div>
  );
}
