import { Activity, Hash, TrendingUp, Wifi, WifiOff, RefreshCw, Zap, Brain, Target, BarChart3, Clock, Signal } from 'lucide-react';
import type { TickData } from '../hooks/useDerivTicks';
import { useDigitAnalysis } from '../hooks/useDigitAnalysis';

interface MarketDataProps {
  tickData: TickData;
  onSwitchSymbol: (symbol: string) => void;
  onReconnect: () => void;
}

const MARKETS = [
  { value: 'R_10', label: 'Volatility 10 Index' },
  { value: 'R_25', label: 'Volatility 25 Index' },
  { value: 'R_50', label: 'Volatility 50 Index' },
  { value: 'R_75', label: 'Volatility 75 Index' },
  { value: 'R_100', label: 'Volatility 100 Index' },
  { value: 'R_10_10S', label: 'Volatility 10 (1s)' },
  { value: 'R_25_10S', label: 'Volatility 25 (1s)' },
  { value: 'R_50_10S', label: 'Volatility 50 (1s)' },
  { value: 'R_75_10S', label: 'Volatility 75 (1s)' },
  { value: 'R_100_10S', label: 'Volatility 100 (1s)' },
];

function DigitBubble({ digit, index, isLatest }: { digit: number; index: number; isLatest: boolean }) {
  const isEven = digit % 2 === 0;

  return (
    <div
      className={`relative flex items-center justify-center w-9 h-9 rounded-xl text-sm font-bold transition-all duration-300 ${
        isLatest ? 'ring-2 ring-cyan-400/50 scale-110 z-10' : ''
      } ${
        isEven
          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
      }`}
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {digit}
      {isLatest && (
        <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
      )}
    </div>
  );
}

function PredictionCard({
  title,
  icon: Icon,
  prediction,
  confidence,
  color,
}: {
  title: string;
  icon: React.ElementType;
  prediction: string | null;
  confidence: number;
  color: string;
}) {
  const gradientClass = color === 'text-blue-400' ? 'from-blue-500/20 to-cyan-500/20' :
    color === 'text-emerald-400' ? 'from-emerald-500/20 to-teal-500/20' : 'from-violet-500/20 to-purple-500/20';

  return (
    <div className={`relative bg-gradient-to-br ${gradientClass} rounded-xl border border-slate-700/30 p-3 overflow-hidden group hover:border-slate-600/50 transition-all`}>
      <div className="absolute inset-0 bg-slate-900/50" />
      <div className="relative">
        <div className="flex items-center gap-1.5 mb-2">
          <Icon className={`w-3.5 h-3.5 ${color}`} />
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">{title}</span>
        </div>
        {prediction ? (
          <div className="flex items-baseline gap-2">
            <span className={`text-lg font-bold ${color}`}>{prediction.toUpperCase()}</span>
            <span className="text-xs text-slate-500">{confidence.toFixed(0)}%</span>
          </div>
        ) : (
          <div className="text-sm font-medium text-slate-500">No signal</div>
        )}
      </div>
    </div>
  );
}

export function MarketData({ tickData, onSwitchSymbol, onReconnect }: MarketDataProps) {
  const { price, lastDigit, digitHistory, symbol, connected, authorized, error, tickCount, latencyMs } = tickData;
  const analysis = useDigitAnalysis(digitHistory);

  return (
    <div className="bg-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-4 sm:px-5 py-4 border-b border-slate-800/50 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Live Market Data</h3>
            <p className="text-[10px] text-slate-500">
              {tickCount > 0 ? `${tickCount} ticks received` : 'Waiting for data...'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {latencyMs > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-400 font-mono">{latencyMs}ms</span>
            </div>
          )}

          <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border ${
            connected
              ? 'bg-emerald-500/10 border-emerald-500/20'
              : 'bg-red-500/10 border-red-500/20'
          }`}>
            {connected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs text-emerald-400 font-medium">{authorized ? 'Authorized' : 'Live'}</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-red-400" />
                <span className="text-xs text-red-400 font-medium">Offline</span>
              </>
            )}
          </div>

          <button
            onClick={onReconnect}
            className="p-2 rounded-lg bg-slate-800/50 hover:bg-slate-700/50 border border-slate-700/50 text-slate-400 hover:text-white transition-all"
            title="Reconnect"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="p-4 sm:p-5 space-y-5">
        {/* Market Selector & Price */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-2">Market</label>
            <select
              value={symbol}
              onChange={(e) => onSwitchSymbol(e.target.value)}
              className="w-full px-3 py-2.5 bg-slate-800/50 border border-slate-700/50 rounded-xl text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all appearance-none cursor-pointer"
            >
              {MARKETS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <TrendingUp className="w-3 h-3 text-cyan-400" />
                <span className="text-[10px] text-slate-500 uppercase">Price</span>
              </div>
              <div className="text-xl font-bold text-white font-mono tracking-tight">
                {price > 0 ? price.toFixed(4) : '—'}
              </div>
            </div>

            <div className="bg-slate-800/50 rounded-xl border border-slate-700/30 p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <Hash className="w-3 h-3 text-violet-400" />
                <span className="text-[10px] text-slate-500 uppercase">Last Digit</span>
              </div>
              <div className="text-xl font-bold text-white font-mono">
                {digitHistory.length > 0 ? lastDigit : '—'}
              </div>
              {digitHistory.length > 0 && (
                <div className="text-[10px] text-slate-500 mt-0.5">
                  {lastDigit % 2 === 0 ? 'Even' : 'Odd'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Predictions */}
        {digitHistory.length >= 10 && (
          <div className="grid grid-cols-3 gap-2">
            <PredictionCard
              title="Even/Odd"
              icon={Zap}
              prediction={analysis.evenOdd.prediction}
              confidence={analysis.evenOdd.confidence}
              color="text-blue-400"
            />
            <PredictionCard
              title="Over/Under"
              icon={Target}
              prediction={analysis.overUnder.prediction}
              confidence={analysis.overUnder.confidence}
              color="text-emerald-400"
            />
            <PredictionCard
              title="Match/Diff"
              icon={Brain}
              prediction={analysis.matchDiff.prediction}
              confidence={analysis.matchDiff.confidence}
              color="text-violet-400"
            />
          </div>
        )}

        {/* Digit Flow */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
              Digit Flow (last {Math.min(digitHistory.length, 20)})
            </span>
            {analysis.hotDigits.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-slate-500">Hot:</span>
                <div className="flex gap-1">
                  {analysis.hotDigits.map((d) => (
                    <span key={d} className="text-[10px] px-1.5 py-0.5 rounded-md bg-orange-500/20 text-orange-400 font-bold">
                      {d}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5 bg-slate-800/30 rounded-xl p-3 border border-slate-700/30">
            {digitHistory.length > 0 ? (
              digitHistory.slice(-20).map((digit, i) => (
                <DigitBubble
                  key={`${i}-${digit}-${tickCount}`}
                  digit={digit}
                  index={i}
                  isLatest={i === digitHistory.slice(-20).length - 1}
                />
              ))
            ) : (
              <div className="flex items-center gap-2 text-xs text-slate-500 w-full justify-center py-4">
                <Signal className="w-4 h-4 animate-pulse" />
                <span>Waiting for ticks...</span>
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        {digitHistory.length > 0 && (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Even/Odd Distribution</div>
              <div className="flex items-center gap-2 mb-2">
                <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-500"
                    style={{ width: `${analysis.evenOdd.evenPercentage}%` }}
                  />
                </div>
                <span className="text-xs text-blue-400 font-bold font-mono w-12 text-right">
                  {analysis.evenOdd.evenPercentage.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>Even: {analysis.evenOdd.evenCount}</span>
                <span>Odd: {analysis.evenOdd.oddCount}</span>
              </div>
              {analysis.evenOdd.streak.count > 2 && (
                <div className="mt-2 text-[10px] text-amber-400 flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  {analysis.evenOdd.streak.type} streak: {analysis.evenOdd.streak.count}
                </div>
              )}
            </div>

            <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Over/Under Distribution</div>
              <div className="flex items-center gap-2 mb-2">
                <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-500"
                    style={{ width: `${analysis.overUnder.overPercentage}%` }}
                  />
                </div>
                <span className="text-xs text-emerald-400 font-bold font-mono w-12 text-right">
                  {analysis.overUnder.overPercentage.toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>Over: {analysis.overUnder.overCount}</span>
                <span>Under: {analysis.overUnder.underCount}</span>
              </div>
              {analysis.overUnder.streak.count > 2 && (
                <div className="mt-2 text-[10px] text-amber-400 flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  {analysis.overUnder.streak.type} streak: {analysis.overUnder.streak.count}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Digit Frequency */}
        {Object.keys(analysis.digitFrequency).length > 0 && (
          <div className="bg-slate-800/30 rounded-xl border border-slate-700/30 p-4">
            <div className="flex items-center gap-2 mb-3">
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Digit Frequency (last 50)</span>
            </div>
            <div className="flex items-end gap-1 h-16">
              {Array.from({ length: 10 }, (_, i) => i).map((digit) => {
                const count = analysis.digitFrequency[digit] || 0;
                const maxCount = Math.max(...Object.values(analysis.digitFrequency));
                const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
                const isHot = analysis.hotDigits.includes(digit);
                const isCold = analysis.coldDigits.includes(digit);

                return (
                  <div key={digit} className="flex-1 flex flex-col items-center gap-1">
                    <div className="w-full bg-slate-700/30 rounded-t-md overflow-hidden relative" style={{ height: '48px' }}>
                      <div
                        className={`absolute bottom-0 w-full rounded-t-md transition-all duration-500 ${
                          isHot ? 'bg-gradient-to-t from-orange-500 to-amber-400' :
                          isCold ? 'bg-slate-600' : 'bg-gradient-to-t from-cyan-500/60 to-blue-500/60'
                        }`}
                        style={{ height: `${height}%` }}
                      />
                    </div>
                    <span className={`text-[10px] font-bold ${isHot ? 'text-orange-400' : isCold ? 'text-slate-500' : 'text-slate-400'}`}>
                      {digit}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
            <WifiOff className="w-4 h-4" />
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
