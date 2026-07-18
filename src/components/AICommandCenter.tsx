import { useState } from 'react';
import {
  Brain,

  TrendingUp,

  Shield,
  Activity,
  Target,
  BarChart3,
  ChevronRight,
  ChevronDown,
  Search,
  Send,
  Lightbulb,
  AlertTriangle,
  CheckCircle2,
  Info,
  RefreshCw,
  FileText,
  PieChart,
  DollarSign,

} from 'lucide-react';

interface AIQuery {
  id: string;
  type: 'market' | 'trade' | 'strategy' | 'risk' | 'portfolio' | 'briefing' | 'anomaly';
  question: string;
  response: AIResponse | null;
  timestamp: Date;
}

interface AIResponse {
  answer: string;
  evidence: EvidenceItem[];
  confidence: number;
  historicalWinRate?: number;
  currentRegime?: string;
  riskScore?: number;
  expectedDrawdown?: number;
  recommendedPositionSize?: number;
}

interface EvidenceItem {
  type: 'pattern' | 'indicator' | 'historical' | 'regime' | 'statistical';
  label: string;
  value: string;
  impact: 'positive' | 'negative' | 'neutral';
}

interface AICommandCenterProps {
  mode?: 'standalone' | 'embedded';
}

export function AICommandCenter({ mode = 'standalone' }: AICommandCenterProps) {
  const [queries, setQueries] = useState<AIQuery[]>([]);
  const [input, setInput] = useState('');
  const [selectedQueryType, setSelectedQueryType] = useState<AIQuery['type']>('market');
  const [isProcessing, setIsProcessing] = useState(false);
  const [expandedResponses, setExpandedResponses] = useState<Set<string>>(new Set());

  const queryTypes = [
    { id: 'market', label: 'Market Analysis', icon: Activity, description: 'Explain current market conditions' },
    { id: 'trade', label: 'Trade Explanation', icon: Target, description: 'Why was this trade recommended?' },
    { id: 'strategy', label: 'Strategy Analysis', icon: BarChart3, description: 'Analyze strategy performance' },
    { id: 'anomaly', label: 'Anomaly Detection', icon: AlertTriangle, description: 'Investigate unusual patterns' },
    { id: 'risk', label: 'Risk Summary', icon: Shield, description: 'Current portfolio risk assessment' },
    { id: 'portfolio', label: 'Portfolio Summary', icon: PieChart, description: 'Overall portfolio overview' },
    { id: 'briefing', label: 'Daily Briefing', icon: FileText, description: 'Morning market briefing' },
  ] as const;

  const generateMockResponse = (type: AIQuery['type'], _question: string): AIResponse => {
    const responses: Record<string, AIResponse> = {
      market: {
        answer: `Based on current market analysis, the Volatility 75 index is showing a bullish momentum with the AI confidence at 87%. Key indicators suggest continuation of the upward trend.`,
        evidence: [
          { type: 'pattern', label: 'Price Action', value: 'Higher highs forming', impact: 'positive' },
          { type: 'indicator', label: 'RSI (14)', value: '62.4 - Bullish territory', impact: 'positive' },
          { type: 'regime', label: 'Market Regime', value: 'Trending - Bullish', impact: 'positive' },
          { type: 'historical', label: 'Similar Patterns Win Rate', value: '84.2%', impact: 'positive' },
        ],
        confidence: 87,
        historicalWinRate: 84.2,
        currentRegime: 'Trending - Bullish',
        riskScore: 35,
        expectedDrawdown: 2.3,
        recommendedPositionSize: 5,
      },
      trade: {
        answer: `This trade was recommended based on multiple confirming signals: a digit pattern match (probability 94.2%), favorable market regime (low volatility), and strong AI confidence.`,
        evidence: [
          { type: 'pattern', label: 'Digit Pattern', value: 'Match: Last 3 digits consistent', impact: 'positive' },
          { type: 'indicator', label: 'Pattern Confidence', value: '94.2%', impact: 'positive' },
          { type: 'regime', label: 'Regime Suitability', value: 'High (Low Volatility)', impact: 'positive' },
          { type: 'statistical', label: 'Historical Success', value: '88% on similar patterns', impact: 'positive' },
        ],
        confidence: 94,
        historicalWinRate: 88,
        currentRegime: 'Low Volatility',
        riskScore: 22,
        expectedDrawdown: 1.8,
        recommendedPositionSize: 8,
      },
      strategy: {
        answer: `Your digit strategy is performing well with an 86% win rate over the last 200 trades. Sharpe ratio of 2.1 indicates good risk-adjusted returns. Consider slight position size increase.`,
        evidence: [
          { type: 'statistical', label: 'Win Rate', value: '86.0%', impact: 'positive' },
          { type: 'statistical', label: 'Sharpe Ratio', value: '2.1', impact: 'positive' },
          { type: 'historical', label: 'Total Trades', value: '200', impact: 'neutral' },
          { type: 'pattern', label: 'Consistency', value: 'Stable across regimes', impact: 'positive' },
        ],
        confidence: 92,
        historicalWinRate: 86,
        riskScore: 28,
      },
      anomaly: {
        answer: `Detected unusual pattern: consecutive losses exceeded threshold (3 trades). This is within expected variance but triggered the alert. No strategy adjustment recommended.`,
        evidence: [
          { type: 'pattern', label: 'Consecutive Losses', value: '3 trades', impact: 'negative' },
          { type: 'statistical', label: 'Expected Variance', value: '±5 trades', impact: 'neutral' },
          { type: 'historical', label: 'Max Drawdown', value: '4.2% (limit: 5%)', impact: 'neutral' },
        ],
        confidence: 78,
        riskScore: 45,
      },
      risk: {
        answer: `Current portfolio risk is LOW. Daily loss is 1.2% (limit: 5%). Consecutive losses: 2 (limit: 5). All risk metrics within safe thresholds.`,
        evidence: [
          { type: 'indicator', label: 'Daily Loss', value: '1.2% of account', impact: 'neutral' },
          { type: 'indicator', label: 'Daily Limit', value: '5.0% (safe)', impact: 'positive' },
          { type: 'indicator', label: 'Consecutive Losses', value: '2 of 5 allowed', impact: 'positive' },
          { type: 'statistical', label: 'VaR (95%)', value: '$127', impact: 'neutral' },
        ],
        confidence: 95,
        riskScore: 25,
      },
      portfolio: {
        answer: `Portfolio summary: Total equity $10,450 (+4.5% today). 3 active strategies. Best performer: Digit Master (92% win rate). Combined exposure: 35% of capital.`,
        evidence: [
          { type: 'statistical', label: 'Total Equity', value: '$10,450', impact: 'positive' },
          { type: 'statistical', label: 'Daily P&L', value: '+$450 (+4.5%)', impact: 'positive' },
          { type: 'indicator', label: 'Active Strategies', value: '3', impact: 'neutral' },
          { type: 'pattern', label: 'Best Strategy', value: 'Digit Master (92%)', impact: 'positive' },
        ],
        confidence: 98,
      },
      briefing: {
        answer: `Good morning! Market outlook: Volatility expected to remain moderate. Recommended focus on digit patterns with 88%+ confidence. High-confidence setups available.`,
        evidence: [
          { type: 'regime', label: 'Expected Volatility', value: 'Moderate', impact: 'neutral' },
          { type: 'indicator', label: 'Market Hours', value: 'Optimal trading window active', impact: 'positive' },
          { type: 'statistical', label: 'Best Setup Availability', value: '12 high-confidence', impact: 'positive' },
          { type: 'pattern', label: 'Recommended Strategy', value: 'Digit Master', impact: 'positive' },
        ],
        confidence: 85,
        currentRegime: 'Moderate Volatility',
      },
    };

    return responses[type] || responses.market;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isProcessing) return;

    setIsProcessing(true);
    
    const newQuery: AIQuery = {
      id: Date.now().toString(),
      type: selectedQueryType,
      question: input,
      response: null,
      timestamp: new Date(),
    };

    setQueries(prev => [newQuery, ...prev]);
    setInput('');

    // Simulate AI processing
    await new Promise(resolve => setTimeout(resolve, 1500));

    const response = generateMockResponse(selectedQueryType, input);
    
    setQueries(prev => 
      prev.map(q => q.id === newQuery.id ? { ...q, response } : q)
    );
    
    setIsProcessing(false);
    setExpandedResponses(prev => new Set([...prev, newQuery.id]));
  };

  const toggleExpanded = (id: string) => {
    setExpandedResponses(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const getEvidenceIcon = (impact: EvidenceItem['impact']) => {
    switch (impact) {
      case 'positive':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'negative':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      default:
        return <Info className="w-4 h-4 text-slate-400" />;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'text-emerald-400';
    if (confidence >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className={`${mode === 'embedded' ? '' : 'min-h-screen bg-slate-950 p-6'}`}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">AI Command Center</h1>
            <p className="text-sm text-slate-400">Get explainable AI insights for your trading</p>
          </div>
        </div>

        {/* Quick Query Types */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {queryTypes.map((type) => (
            <button
              key={type.id}
              onClick={() => setSelectedQueryType(type.id as AIQuery['type'])}
              className={`p-4 rounded-xl border text-left transition-all ${
                selectedQueryType === type.id
                  ? 'bg-blue-500/10 border-blue-500/50 text-white'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
              }`}
            >
              <type.icon className={`w-5 h-5 mb-2 ${
                selectedQueryType === type.id ? 'text-blue-400' : 'text-slate-500'
              }`} />
              <p className="font-medium text-sm">{type.label}</p>
            </button>
          ))}
        </div>

        {/* Query Input */}
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask about ${queryTypes.find(t => t.id === selectedQueryType)?.description.toLowerCase() || 'trading'}...`}
              className="w-full pl-12 pr-32 py-4 bg-slate-900 border border-slate-800 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isProcessing}
            />
            <button
              type="submit"
              disabled={!input.trim() || isProcessing}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg font-medium text-sm flex items-center gap-2 transition-colors"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Ask AI
                </>
              )}
            </button>
          </div>
        </form>

        {/* Query History */}
        <div className="space-y-4">
          {queries.length === 0 ? (
            <div className="text-center py-12 text-slate-500">
              <Lightbulb className="w-12 h-12 mx-auto mb-4 text-slate-600" />
              <p>Ask a question above to get AI-powered insights</p>
            </div>
          ) : (
            queries.map((query) => (
              <div
                key={query.id}
                className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden"
              >
                {/* Query Header */}
                <div className="p-4 border-b border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2 py-1 bg-slate-800 text-blue-400 text-xs rounded-full font-medium">
                      {queryTypes.find(t => t.id === query.type)?.label}
                    </span>
                    <span className="text-xs text-slate-500">
                      {query.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-white font-medium">{query.question}</p>
                </div>

                {/* Response */}
                {query.response && (
                  <div className="p-4">
                    {/* Main Answer */}
                    <div className="flex items-start gap-3 mb-4">
                      <Brain className="w-5 h-5 text-blue-400 mt-1 flex-shrink-0" />
                      <p className="text-slate-300 leading-relaxed">{query.response.answer}</p>
                    </div>

                    {/* Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                      <div className="bg-slate-800/50 rounded-lg p-3">
                        <div className="flex items-center gap-2 mb-1">
                          <Target className="w-4 h-4 text-slate-500" />
                          <span className="text-xs text-slate-500">Confidence</span>
                        </div>
                        <p className={`text-xl font-bold ${getConfidenceColor(query.response.confidence)}`}>
                          {query.response.confidence}%
                        </p>
                      </div>
                      
                      {query.response.historicalWinRate && (
                        <div className="bg-slate-800/50 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <TrendingUp className="w-4 h-4 text-slate-500" />
                            <span className="text-xs text-slate-500">Historical Win Rate</span>
                          </div>
                          <p className="text-xl font-bold text-emerald-400">
                            {query.response.historicalWinRate}%
                          </p>
                        </div>
                      )}

                      {query.response.riskScore !== undefined && (
                        <div className="bg-slate-800/50 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <Shield className="w-4 h-4 text-slate-500" />
                            <span className="text-xs text-slate-500">Risk Score</span>
                          </div>
                          <p className={`text-xl font-bold ${
                            query.response.riskScore < 30 ? 'text-emerald-400' :
                            query.response.riskScore < 60 ? 'text-amber-400' : 'text-red-400'
                          }`}>
                            {query.response.riskScore}
                          </p>
                        </div>
                      )}

                      {query.response.recommendedPositionSize && (
                        <div className="bg-slate-800/50 rounded-lg p-3">
                          <div className="flex items-center gap-2 mb-1">
                            <DollarSign className="w-4 h-4 text-slate-500" />
                            <span className="text-xs text-slate-500">Position Size</span>
                          </div>
                          <p className="text-xl font-bold text-white">
                            {query.response.recommendedPositionSize}%
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Evidence Section */}
                    <div className="border-t border-slate-800 pt-4">
                      <button
                        onClick={() => toggleExpanded(query.id)}
                        className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-3"
                      >
                        {expandedResponses.has(query.id) ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                        <span className="text-sm font-medium">Supporting Evidence</span>
                      </button>

                      {expandedResponses.has(query.id) && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {query.response.evidence.map((item, index) => (
                            <div
                              key={index}
                              className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg"
                            >
                              {getEvidenceIcon(item.impact)}
                              <div>
                                <p className="text-xs text-slate-500">{item.label}</p>
                                <p className="text-sm text-white font-medium">{item.value}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Additional Context */}
                    <div className="flex flex-wrap gap-2 mt-4">
                      {query.response.currentRegime && (
                        <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full">
                          Regime: {query.response.currentRegime}
                        </span>
                      )}
                      {query.response.expectedDrawdown !== undefined && (
                        <span className="px-2 py-1 bg-slate-800 text-slate-400 text-xs rounded-full">
                          Expected Drawdown: {query.response.expectedDrawdown}%
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
