import { useState, useEffect } from 'react';
import { ShoppingCart, ArrowUp, ArrowDown, Hash, Zap, Target, Brain, DollarSign, Clock, AlertTriangle, CheckCircle, XCircle, Loader2, Ban, Scale, Sparkles, TrendingUp } from 'lucide-react';
import type { TickData } from '../hooks/useDerivTicks';
import { useDigitAnalysis } from '../hooks/useDigitAnalysis';
import { useTradeExecution, type ContractType } from '../hooks/useTradeExecution';
import { useAdaptivePositionSizing } from '../hooks/useAdaptivePositionSizing';
import type { RegimeState } from '../hooks/useRegimeDetection';

interface TradeExecutionPanelProps {
  tickData: TickData;
  apiToken?: string;
  regimeState?: RegimeState;
  isStrategyAllowed?: (strategyType: string) => { allowed: boolean; reason: string };
  onBuildEvidence?: (
    symbol: string, contractType: string, amount: number, digitHistory: number[], price: number,
    regime: string, regimeConfidence: number, sizingAdjustments: { name: string; factor: number }[],
    isStrategyAllowed: boolean, strategyBlockReason: string, isGloballyBlocked: boolean, globalBlockReason: string | null,
  ) => { blocked: boolean; blockReason: string | null; id: string };
  onGenerateShadowSignal?: (
    symbol: string, contractType: string, predictedDirection: string, confidence: number,
    expectedOutcome: 'win' | 'loss', expectedPnl: number, latencyMs: number,
  ) => { id: string };
  onAddJournalEntry?: (entry: {
    timestamp: number; symbol: string; contractType: string; entryPrice: number; entryDigit: number;
    amount: number; confidence: number; regime: string; entryConditions: string[]; exitConditions: string[]; notes: string;
  }) => { id: string };
}

const CONTRACT_TYPES: { type: ContractType; label: string; icon: React.ElementType; color: string; gradient: string; desc: string; strategyType: string }[] = [
  { type: 'DIGITEVEN', label: 'Even', icon: Zap, color: 'text-blue-400', gradient: 'from-blue-500 to-cyan-500', desc: 'Last digit is even', strategyType: 'even_odd' },
  { type: 'DIGITODD', label: 'Odd', icon: Zap, color: 'text-amber-400', gradient: 'from-amber-500 to-orange-500', desc: 'Last digit is odd', strategyType: 'even_odd' },
  { type: 'DIGITOVER', label: 'Over', icon: ArrowUp, color: 'text-emerald-400', gradient: 'from-emerald-500 to-teal-500', desc: 'Last digit > barrier', strategyType: 'over_under' },
  { type: 'DIGITUNDER', label: 'Under', icon: ArrowDown, color: 'text-red-400', gradient: 'from-red-500 to-rose-500', desc: 'Last digit < barrier', strategyType: 'over_under' },
  { type: 'DIGITMATCH', label: 'Match', icon: Target, color: 'text-violet-400', gradient: 'from-violet-500 to-purple-500', desc: 'Last digit matches', strategyType: 'match_diff' },
  { type: 'DIGITDIFF', label: 'Diff', icon: Brain, color: 'text-cyan-400', gradient: 'from-cyan-500 to-blue-500', desc: 'Last digit differs', strategyType: 'match_diff' },
];

export function TradeExecutionPanel({ tickData, apiToken, regimeState, isStrategyAllowed, onBuildEvidence, onGenerateShadowSignal, onAddJournalEntry }: TradeExecutionPanelProps) {
  const [selectedType, setSelectedType] = useState<ContractType>('DIGITEVEN');
  const [amount, setAmount] = useState(1);
  const [duration, setDuration] = useState(5);
  const [barrier, setBarrier] = useState('5');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const analysis = useDigitAnalysis(tickData.digitHistory);
  const { executeTrade, executing, lastResult } = useTradeExecution(apiToken);
  const sizing = useAdaptivePositionSizing({ baseAmount: 1.0, maxRiskPerTrade: 0.02 });

  const needsBarrier = selectedType === 'DIGITOVER' || selectedType === 'DIGITUNDER';
  const needsPrediction = selectedType === 'DIGITMATCH' || selectedType === 'DIGITDIFF';

  const selectedStrategyType = CONTRACT_TYPES.find(c => c.type === selectedType)?.strategyType || '';

  const regimeCheck = isStrategyAllowed && selectedStrategyType
    ? isStrategyAllowed(selectedStrategyType)
    : { allowed: true, reason: '' };

  const isGloballyBlocked = regimeState && !regimeState.isTradeable;

  const confidence = analysis.evenOdd.confidence || analysis.overUnder.confidence || analysis.matchDiff.confidence || 50;
  const sizingResult = sizing.calculateSize(confidence, selectedStrategyType, tickData.digitHistory.map(() => tickData.price));

  useEffect(() => {
    if (!sizingResult.blocked && sizingResult.size > 0) {
      setAmount(sizingResult.size);
    }
  }, [sizingResult.size, sizingResult.blocked]);

  const handleTrade = async () => {
    setError(null);
    setSuccess(null);

    if (!apiToken) {
      setError('API token required. Set VITE_DERIV_API_TOKEN in your .env file.');
      return;
    }

    if (!tickData.connected) {
      setError('Not connected to Deriv. Please wait for connection.');
      return;
    }

    if (isGloballyBlocked) {
      setError(regimeState?.blockReason || 'Trading blocked by regime detector.');
      return;
    }

    if (!regimeCheck.allowed) {
      setError(regimeCheck.reason);
      return;
    }

    if (amount < 0.35) {
      setError('Minimum trade amount is $0.35');
      return;
    }

    const req = {
      contract_type: selectedType,
      symbol: tickData.symbol,
      amount,
      duration,
      duration_unit: 't' as const,
      ...(needsBarrier ? { barrier } : {}),
      ...(needsPrediction ? { prediction: barrier } : {}),
    };

    if (onBuildEvidence) {
      const evidence = onBuildEvidence(
        tickData.symbol, selectedType, amount, tickData.digitHistory, tickData.price,
        regimeState?.currentRegime || 'random', regimeState?.confidence || 0, sizingResult.adjustments,
        regimeCheck.allowed, regimeCheck.reason, isGloballyBlocked || false, regimeState?.blockReason || null,
      );
      if (evidence.blocked) {
        setError(evidence.blockReason || 'Trade blocked by evidence system');
        return;
      }
    }

    if (onGenerateShadowSignal) {
      onGenerateShadowSignal(
        tickData.symbol, selectedType,
        selectedType.includes('EVEN') || selectedType.includes('OVER') || selectedType.includes('MATCH') ? 'up' : 'down',
        confidence, 'win', amount * 0.94, tickData.latencyMs,
      );
    }

    if (onAddJournalEntry) {
      onAddJournalEntry({
        timestamp: Date.now(), symbol: tickData.symbol, contractType: selectedType,
        entryPrice: tickData.price, entryDigit: tickData.lastDigit, amount, confidence,
        regime: regimeState?.currentRegime || 'random',
        entryConditions: [`Regime: ${regimeState?.currentRegime || 'unknown'}`, `Confidence: ${confidence}%`, `Strategy: ${selectedStrategyType}`],
        exitConditions: [], notes: `Adaptive size: ${amount.toFixed(2)}`,
      });
    }

    const result = await executeTrade(req);

    if (result.success) {
      setSuccess(`Trade placed! Contract ID: ${result.contract_id?.slice(-8)} | Buy: ${result.buy_price?.toFixed(2)} | Payout: ${result.payout?.toFixed(2)}`);
    } else {
      setError(result.error || 'Trade failed');
    }
  };

  const getRecommendedType = (): ContractType | null => {
    if (analysis.evenOdd.prediction && analysis.evenOdd.confidence > 60) {
      return analysis.evenOdd.prediction === 'even' ? 'DIGITEVEN' : 'DIGITODD';
    }
    if (analysis.overUnder.prediction && analysis.overUnder.confidence > 60) {
      return analysis.overUnder.prediction === 'over' ? 'DIGITOVER' : 'DIGITUNDER';
    }
    if (analysis.matchDiff.prediction && analysis.matchDiff.confidence > 60) {
      return analysis.matchDiff.prediction === 'match' ? 'DIGITMATCH' : 'DIGITDIFF';
    }
    return null;
  };

  const recommended = getRecommendedType();

  return (
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <ShoppingCart className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Manual Trade</h3>
            <p className="text-[10px] text-slate-500">Execute trades with AI assistance</p>
          </div>
        </div>

        {!apiToken && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[10px] text-amber-400 font-medium">Demo Mode</span>
          </div>
        )}
      </div>

      <div className="p-4 sm:p-5 space-y-5">
        {/* Block Banners */}
        {isGloballyBlocked && (
          <div className="flex items-center gap-3 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
            <Ban className="w-4 h-4 text-red-400 shrink-0" />
            <span className="text-xs text-red-400">{regimeState?.blockReason}</span>
          </div>
        )}

        {!isGloballyBlocked && !regimeCheck.allowed && (
          <div className="flex items-center gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="text-xs text-amber-400">{regimeCheck.reason}</span>
          </div>
        )}

        {/* Contract Type Selector */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
          {CONTRACT_TYPES.map((ct) => {
            const Icon = ct.icon;
            const isSelected = selectedType === ct.type;
            const isRecommended = recommended === ct.type;
            const stratCheck = isStrategyAllowed ? isStrategyAllowed(ct.strategyType) : { allowed: true };
            const isBlocked = !stratCheck.allowed;

            return (
              <button
                key={ct.type}
                onClick={() => !isBlocked && setSelectedType(ct.type)}
                disabled={isBlocked}
                className={`relative flex flex-col items-center gap-1.5 p-3 rounded-xl border transition-all group ${
                  isSelected
                    ? `bg-gradient-to-br ${ct.gradient} bg-opacity-20 border-transparent ring-2 ring-${ct.color.replace('text-', '')}/50`
                    : isBlocked
                    ? 'bg-slate-800/30 border-slate-700/30 opacity-40 cursor-not-allowed'
                    : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
                }`}
              >
                {isRecommended && (
                  <div className="absolute -top-1 -right-1 px-1.5 py-0.5 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-[8px] font-bold flex items-center gap-0.5 shadow-lg">
                    <Sparkles className="w-2.5 h-2.5" /> AI
                  </div>
                )}
                {isBlocked && (
                  <div className="absolute -top-1 -right-1 px-1.5 py-0.5 rounded-full bg-red-500 text-white text-[8px] font-bold">
                    BLOCK
                  </div>
                )}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  isSelected ? `bg-gradient-to-br ${ct.gradient}` : 'bg-slate-700'
                }`}>
                  <Icon className={`w-4 h-4 ${isSelected ? 'text-white' : ct.color}`} />
                </div>
                <span className={`text-[10px] font-medium ${isSelected ? ct.color : 'text-slate-300'}`}>
                  {ct.label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Adaptive Sizing Info */}
        {sizingResult.adjustments.length > 0 && (
          <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Scale className="w-4 h-4 text-cyan-400" />
              <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">Adaptive Position Sizing</span>
            </div>
            <div className="space-y-1.5">
              {sizingResult.adjustments.map((adj, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">{adj.name}</span>
                  <span className={`font-bold font-mono ${adj.factor < 1 ? 'text-red-400' : adj.factor > 1 ? 'text-emerald-400' : 'text-slate-300'}`}>
                    {adj.factor < 1 ? '' : '+'}{((adj.factor - 1) * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
              <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-700/50">
                <span className="text-slate-300 font-medium">Final Size</span>
                <span className="text-cyan-400 font-bold font-mono">${sizingResult.size.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Trade Parameters */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="flex items-center gap-1.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-2">
              <DollarSign className="w-3 h-3" /> Amount (USD)
            </label>
            <input
              type="number"
              min={0.35}
              max={50000}
              step={0.01}
              value={amount}
              onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
              disabled={sizingResult.blocked}
              className="w-full px-3 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-xl text-sm text-white font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50"
            />
          </div>

          <div>
            <label className="flex items-center gap-1.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-2">
              <Clock className="w-3 h-3" /> Duration (ticks)
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value) || 1)}
              className="w-full px-3 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-xl text-sm text-white font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
            />
          </div>

          {(needsBarrier || needsPrediction) && (
            <div>
              <label className="flex items-center gap-1.5 text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-2">
                <Hash className="w-3 h-3" /> {needsBarrier ? 'Barrier' : 'Prediction'} (0-9)
              </label>
              <input
                type="number"
                min={0}
                max={9}
                value={barrier}
                onChange={(e) => setBarrier(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-xl text-sm text-white font-mono focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
              />
            </div>
          )}
        </div>

        {/* AI Recommendation */}
        {recommended && recommended !== selectedType && (
          <div className="flex items-center gap-3 p-3 rounded-xl bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-500/20">
            <TrendingUp className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-blue-300 flex-1">
              AI recommends <strong className="text-blue-400">{CONTRACT_TYPES.find((c) => c.type === recommended)?.label}</strong> based on current patterns
            </span>
            <button
              onClick={() => setSelectedType(recommended)}
              className="text-[10px] px-2.5 py-1 rounded-lg bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 font-medium transition-all"
            >
              Apply
            </button>
          </div>
        )}

        {/* Execute Button */}
        <button
          onClick={handleTrade}
          disabled={executing || !tickData.connected || isGloballyBlocked || !regimeCheck.allowed}
          className={`w-full flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl text-sm font-bold transition-all ${
            executing || !tickData.connected || isGloballyBlocked || !regimeCheck.allowed
              ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30'
          }`}
        >
          {executing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Placing Trade...
            </>
          ) : !tickData.connected ? (
            <>
              <Clock className="w-5 h-5" />
              Waiting for Connection...
            </>
          ) : isGloballyBlocked || !regimeCheck.allowed ? (
            <>
              <Ban className="w-5 h-5" />
              Trading Blocked
            </>
          ) : (
            <>
              <ShoppingCart className="w-5 h-5" />
              Place {CONTRACT_TYPES.find((c) => c.type === selectedType)?.label} @ ${amount.toFixed(2)}
            </>
          )}
        </button>

        {/* Status Messages */}
        {error && (
          <div className="flex items-center gap-3 p-3 rounded-xl bg-red-500/10 border border-red-500/20">
            <XCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span className="text-xs text-red-400">{error}</span>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="text-xs text-emerald-400">{success}</span>
          </div>
        )}

        {lastResult && lastResult.success && !success && (
          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/50 border border-slate-700/50">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <div className="text-xs text-slate-300 flex-1">
              <span className="font-medium text-white">Last Trade:</span> Contract {lastResult.contract_id?.slice(-8)} |{' '}
              {lastResult.status === 'won' ? (
                <span className="text-emerald-400 font-medium">+${lastResult.profit?.toFixed(2)}</span>
              ) : lastResult.status === 'lost' ? (
                <span className="text-red-400 font-medium">-${Math.abs(lastResult.profit || 0).toFixed(2)}</span>
              ) : (
                <span className="text-blue-400">Open</span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
