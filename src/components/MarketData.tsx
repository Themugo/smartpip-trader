import { Activity, Hash, TrendingUp, Wifi, WifiOff, RefreshCw, Zap, Brain, Target, BarChart3, Clock } from 'lucide-react';
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
  const isHigh = digit >= 5;

  return (
    <div
      className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold transition-all duration-300 ${
        isLatest
          ? 'ring-2 ring-white scale-110'
          : ''
      } ${
        isEven
          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
          : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
      }`}
      style={{ animationDelay: `${index * 30}ms` }}
      title={`${isEven ? 'Even' : 'Odd'} | ${isHigh ? 'Over' : 'Under'} 5`}
    >
      {digit}
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
  if (!prediction) {
    return (
      <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3 opacity-60">
        <div className="flex items-center gap-1.5 mb-1">
          <Icon className={`w-3.5 h-3.5 ${color}`} />
          <span className="text-xs text-slate-400">{title}</span>
        </div>
        <div className="text-sm font-medium text-slate-500">No clear signal</div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className={`w-3.5 h-3.5 ${color}`} />
        <span className="text-xs text-slate-400">{title}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-lg font-bold ${color}`}>{prediction.toUpperCase()}</span>
        <span className="text-xs text-slate-500">{confidence.toFixed(0)}% conf</span>
      </div>
    </div>
  );
}

export function MarketData({ tickData, onSwitchSymbol, onReconnect }: MarketDataProps) {
  const { price, lastDigit, digitHistory, symbol, connected, authorized, error, tickCount, latencyMs } = tickData;
  const analysis = useDigitAnalysis(digitHistory);

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h3 className="text-sm font-semibold text-slate-200">Live Market Data</h3>
          {tickCount > 0 && (
            <span className="text-xs text-slate-500">({tickCount} ticks)</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {latencyMs > 0 && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-slate-900 border border-slate-700/50">
              <Clock className="w-3 h-3 text-slate-400" />
              <span className="text-[10px] text-slate-400">{latencyMs}ms</span>
            </div>
          )}
          {connected ? (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs text-emerald-400 font-medium">{authorized ? 'Authorized' : 'Live'}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-red-500/10 border border-red-500/20">
              <WifiOff className="w-3.5 h-3.5 text-red-400" />
              <span className="text-xs text-red-400 font-medium">Disconnected</span>
            </div>
          )}
          <button
            onClick={onReconnect}
            className="p-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors"
            title="Reconnect"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Market Selector */}
      <div>
        <label className="block text-xs text-slate-400 mb-1.5">Market</label>
        <select
          value={symbol}
          onChange={(e) => onSwitchSymbol(e.target.value)}
          className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
        >
          {MARKETS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      {/* Price Display */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs text-slate-400">Current Price</span>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight font-mono">
            {price > 0 ? price.toFixed(4) : '—'}
          </div>
        </div>

        <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
          <div className="flex items-center gap-1.5 mb-1">
            <Hash className="w-3.5 h-3.5 text-violet-400" />
            <span className="text-xs text-slate-400">Last Digit</span>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight font-mono">
            {digitHistory.length > 0 ? lastDigit : '—'}
          </div>
          {digitHistory.length > 0 && (
            <div className="text-xs text-slate-500 mt-0.5">
              {lastDigit % 2 === 0 ? 'Even' : 'Odd'} | {lastDigit >= 5 ? 'Over' : 'Under'} 5
            </div>
          )}
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
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-400">Digit Flow (last {Math.min(digitHistory.length, 20)})</span>
          {analysis.hotDigits.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-slate-500">Hot:</span>
              <div className="flex gap-1">
                {analysis.hotDigits.map((d) => (
                  <span key={d} className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400 font-medium">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
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
            <span className="text-xs text-slate-500">Waiting for ticks...</span>
          )}
        </div>
      </div>

      {/* Stats */}
      {digitHistory.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="text-xs text-slate-400 mb-1">Even/Odd Distribution</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full transition-all duration-500"
                  style={{ width: `${analysis.evenOdd.evenPercentage}%` }}
                />
              </div>
              <span className="text-xs text-blue-400 font-medium">{analysis.evenOdd.evenPercentage.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-slate-500">Even: {analysis.evenOdd.evenCount}</span>
              <span className="text-[10px] text-slate-500">Odd: {analysis.evenOdd.oddCount}</span>
            </div>
            {analysis.evenOdd.streak.count > 2 && (
              <div className="mt-1 text-[10px] text-amber-400">
                {analysis.evenOdd.streak.type} streak: {analysis.evenOdd.streak.count}
              </div>
            )}
          </div>

          <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
            <div className="text-xs text-slate-400 mb-1">Over/Under Distribution</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                  style={{ width: `${analysis.overUnder.overPercentage}%` }}
                />
              </div>
              <span className="text-xs text-emerald-400 font-medium">{analysis.overUnder.overPercentage.toFixed(1)}%</span>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-slate-500">Over: {analysis.overUnder.overCount}</span>
              <span className="text-[10px] text-slate-500">Under: {analysis.overUnder.underCount}</span>
            </div>
            {analysis.overUnder.streak.count > 2 && (
              <div className="mt-1 text-[10px] text-amber-400">
                {analysis.overUnder.streak.type} streak: {analysis.overUnder.streak.count}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Digit Frequency Bar Chart */}
      {Object.keys(analysis.digitFrequency).length > 0 && (
        <div className="bg-slate-900 rounded-lg border border-slate-700/50 p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400">Digit Frequency (last 50)</span>
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
                  <div className="w-full bg-slate-800 rounded-t overflow-hidden relative" style={{ height: '48px' }}>
                    <div
                      className={`absolute bottom-0 w-full rounded-t transition-all duration-500 ${
                        isHot ? 'bg-orange-500' : isCold ? 'bg-slate-600' : 'bg-cyan-500/60'
                      }`}
                      style={{ height: `${height}%` }}
                    />
                  </div>
                  <span className={`text-[10px] font-medium ${isHot ? 'text-orange-400' : isCold ? 'text-slate-500' : 'text-slate-400'}`}>
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
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
          {error}
        </div>
      )}
    </div>
  );
}
