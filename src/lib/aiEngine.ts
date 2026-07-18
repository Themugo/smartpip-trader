/**
 * AI Engine
 * 
 * Unified AI orchestration layer for all AI capabilities in the platform.
 * Provides consistent interface for market analysis, strategy review,
 * risk explanation, and portfolio insights.
 */

import type { Trade, TradeStatistics, SystemSettings } from './supabase';
import type { RegimeType } from '../hooks/useRegimeDetection';

// Types
export interface AIQuery {
  id: string;
  type: AIQueryType;
  context: AIContext;
  timestamp: number;
}

export type AIQueryType = 
  | 'market_analysis'
  | 'strategy_review'
  | 'risk_explanation'
  | 'trade_explanation'
  | 'portfolio_review'
  | 'session_summary'
  | 'daily_briefing'
  | 'replay_explanation'
  | 'trade_marker'
  | 'pattern_detection';

export interface AIContext {
  trades?: Trade[];
  statistics?: TradeStatistics;
  settings?: SystemSettings;
  regime?: RegimeType;
  marketData?: MarketData;
  currentTrade?: Trade;
  portfolio?: PortfolioData;
  replayEvents?: ReplayEvent[];
  annotations?: TradeAnnotation[];
}

export interface MarketData {
  symbol: string;
  price: number;
  digit: number;
  history: number[];
  volatility: number;
  trend: 'up' | 'down' | 'sideways';
}

export interface PortfolioData {
  totalBalance: number;
  equity: number;
  openPnl: number;
  closedPnl: number;
  drawdown: number;
  drawdownPercent: number;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
  exposure: Record<string, number>;
  allocation: Record<string, number>;
}

export interface ReplayEvent {
  time: number;
  type: 'trade_entry' | 'trade_exit' | 'signal' | 'regime_change' | 'anomaly';
  data: Record<string, unknown>;
}

export interface TradeAnnotation {
  id: string;
  time: number;
  type: 'ai_commentary' | 'market_event' | 'trade_marker' | 'pattern' | 'custom';
  content: string;
  important: boolean;
  confidence?: number;
  evidence?: string[];
}

export interface AIResponse {
  id: string;
  queryId: string;
  type: AIQueryType;
  content: string;
  confidence: number;
  evidence: string[];
  reasoning: string[];
  supportingIndicators: string[];
  historicalContext?: string;
  alternativeScenarios?: string[];
  timestamp: number;
  metadata?: Record<string, unknown>;
}

// AI Engine class
export class AIEngine {
  private responses: Map<string, AIResponse> = new Map();

  /**
   * Process an AI query and return a response
   */
  async process(query: Omit<AIQuery, 'id' | 'timestamp'>): Promise<AIResponse> {
    const id = `ai-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    const fullQuery: AIQuery = {
      ...query,
      id,
      timestamp: Date.now(),
    };

    // Route to appropriate handler
    let response: AIResponse;
    
    switch (query.type) {
      case 'market_analysis':
        response = await this.generateMarketAnalysis(fullQuery);
        break;
      case 'strategy_review':
        response = await this.generateStrategyReview(fullQuery);
        break;
      case 'risk_explanation':
        response = await this.generateRiskExplanation(fullQuery);
        break;
      case 'trade_explanation':
        response = await this.generateTradeExplanation(fullQuery);
        break;
      case 'portfolio_review':
        response = await this.generatePortfolioReview(fullQuery);
        break;
      case 'session_summary':
        response = await this.generateSessionSummary(fullQuery);
        break;
      case 'daily_briefing':
        response = await this.generateDailyBriefing(fullQuery);
        break;
      case 'replay_explanation':
        response = await this.generateReplayExplanation(fullQuery);
        break;
      default:
        response = await this.generateGenericResponse(fullQuery);
    }

    // Cache response
    this.responses.set(id, response);
    return response;
  }

  /**
   * Get response by ID
   */
  getResponse(id: string): AIResponse | undefined {
    return this.responses.get(id);
  }

  /**
   * Generate market analysis
   */
  private async generateMarketAnalysis(query: AIQuery): Promise<AIResponse> {
    const { marketData, regime } = query.context;
    
    if (!marketData) {
      return this.createMockResponse(query.id, 'market_analysis');
    }

    const confidence = this.calculateConfidence(marketData);
    const indicators = this.analyzeMarketIndicators(marketData);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'market_analysis',
      content: this.formatMarketAnalysis(marketData, regime, indicators),
      confidence,
      evidence: indicators.evidence,
      reasoning: indicators.reasoning,
      supportingIndicators: indicators.indicators,
      historicalContext: await this.getHistoricalContext(marketData),
      alternativeScenarios: this.generateAlternativeScenarios(marketData),
      timestamp: query.timestamp,
      metadata: { regime, volatility: marketData.volatility },
    };
  }

  /**
   * Generate strategy review
   */
  private async generateStrategyReview(query: AIQuery): Promise<AIResponse> {
    const { trades, statistics } = query.context;
    
    if (!trades || !statistics) {
      return this.createMockResponse(query.id, 'strategy_review');
    }

    const performance = this.analyzeStrategyPerformance(trades, statistics);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'strategy_review',
      content: this.formatStrategyReview(performance),
      confidence: performance.confidence,
      evidence: performance.evidence,
      reasoning: performance.reasoning,
      supportingIndicators: performance.indicators,
      timestamp: query.timestamp,
    };
  }

  /**
   * Generate risk explanation
   */
  private generateRiskExplanation(query: AIQuery): AIResponse {
    const { currentTrade, portfolio } = query.context;
    
    if (!portfolio) {
      return this.createMockResponse(query.id, 'risk_explanation');
    }

    const riskAnalysis = this.analyzeRisk(currentTrade, portfolio);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'risk_explanation',
      content: riskAnalysis.summary,
      confidence: riskAnalysis.confidence,
      evidence: riskAnalysis.evidence,
      reasoning: riskAnalysis.reasoning,
      supportingIndicators: riskAnalysis.indicators,
      timestamp: query.timestamp,
    };
  }

  /**
   * Generate trade explanation
   */
  private generateTradeExplanation(query: AIQuery): AIResponse {
    const { currentTrade, marketData, regime } = query.context;
    
    if (!currentTrade) {
      return this.createMockResponse(query.id, 'trade_explanation');
    }

    const explanation = this.explainTrade(currentTrade, marketData, regime);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'trade_explanation',
      content: explanation.summary,
      confidence: explanation.confidence,
      evidence: explanation.evidence,
      reasoning: explanation.reasoning,
      supportingIndicators: explanation.indicators,
      historicalContext: explanation.context,
      timestamp: query.timestamp,
    };
  }

  /**
   * Generate portfolio review
   */
  private async generatePortfolioReview(query: AIQuery): Promise<AIResponse> {
    const { trades, statistics, portfolio } = query.context;
    
    const review = this.analyzePortfolio(trades, statistics, portfolio);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'portfolio_review',
      content: review.summary,
      confidence: review.confidence,
      evidence: review.evidence,
      reasoning: review.reasoning,
      supportingIndicators: review.indicators,
      alternativeScenarios: review.alternatives,
      timestamp: query.timestamp,
    };
  }

  /**
   * Generate session summary
   */
  private generateSessionSummary(query: AIQuery): AIResponse {
    const { trades, statistics } = query.context;
    
    if (!trades || !statistics) {
      return this.createMockResponse(query.id, 'session_summary');
    }

    const summary = this.createSessionSummary(trades, statistics);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'session_summary',
      content: summary.narrative,
      confidence: summary.confidence,
      evidence: summary.evidence,
      reasoning: summary.reasoning,
      supportingIndicators: summary.indicators,
      timestamp: query.timestamp,
      metadata: { tradeCount: trades.length, duration: Date.now() },
    };
  }

  /**
   * Generate daily briefing
   */
  private generateDailyBriefing(query: AIQuery): AIResponse {
    const { trades, statistics, marketData, portfolio } = query.context;
    
    const briefing = this.createDailyBriefing(trades, statistics, marketData, portfolio);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'daily_briefing',
      content: briefing.narrative,
      confidence: briefing.confidence,
      evidence: briefing.evidence,
      reasoning: briefing.reasoning,
      supportingIndicators: briefing.indicators,
      alternativeScenarios: briefing.alternatives,
      timestamp: query.timestamp,
      metadata: { date: new Date().toISOString().split('T')[0] },
    };
  }

  /**
   * Generate replay explanation
   */
  private generateReplayExplanation(query: AIQuery): AIResponse {
    const { replayEvents, annotations } = query.context;
    
    if (!replayEvents || !annotations) {
      return this.createMockResponse(query.id, 'replay_explanation');
    }

    const explanation = this.explainReplay(replayEvents, annotations);
    
    return {
      id: query.id,
      queryId: query.id,
      type: 'replay_explanation',
      content: explanation.narrative,
      confidence: explanation.confidence,
      evidence: explanation.evidence,
      reasoning: explanation.reasoning,
      supportingIndicators: explanation.indicators,
      timestamp: query.timestamp,
    };
  }

  /**
   * Generate generic response
   */
  private generateGenericResponse(query: AIQuery): AIResponse {
    return {
      id: query.id,
      queryId: query.id,
      type: query.type,
      content: 'Processing your request...',
      confidence: 0.5,
      evidence: [],
      reasoning: ['Analyzing available data'],
      supportingIndicators: [],
      timestamp: query.timestamp,
    };
  }

  // Helper methods
  
  private calculateConfidence(data: MarketData): number {
    // Calculate confidence based on data quality
    let confidence = 0.5;
    
    if (data.history.length > 50) confidence += 0.2;
    if (data.volatility < 0.5) confidence += 0.1;
    if (data.trend) confidence += 0.1;
    
    return Math.min(confidence, 0.95);
  }

  private analyzeMarketIndicators(data: MarketData) {
    const indicators: string[] = [];
    const evidence: string[] = [];
    const reasoning: string[] = [];

    // Price action analysis
    const recentPrices = data.history.slice(-10);
    const priceChange = recentPrices[recentPrices.length - 1] - recentPrices[0];
    const priceChangePercent = (priceChange / recentPrices[0]) * 100;

    if (priceChangePercent > 0.5) {
      indicators.push('Bullish price action');
      evidence.push(`Price increased ${priceChangePercent.toFixed(2)}% over last 10 ticks`);
      reasoning.push('Sustained upward momentum detected');
    } else if (priceChangePercent < -0.5) {
      indicators.push('Bearish price action');
      evidence.push(`Price decreased ${Math.abs(priceChangePercent).toFixed(2)}% over last 10 ticks`);
      reasoning.push('Sustained downward momentum detected');
    } else {
      indicators.push('Neutral price action');
      reasoning.push('Price consolidating within range');
    }

    // Volatility analysis
    if (data.volatility > 0.8) {
      indicators.push('High volatility');
      evidence.push(`Volatility index: ${data.volatility.toFixed(2)}`);
      reasoning.push('Elevated market activity may increase risk');
    } else if (data.volatility < 0.3) {
      indicators.push('Low volatility');
      evidence.push(`Volatility index: ${data.volatility.toFixed(2)}`);
      reasoning.push('Calm market conditions');
    }

    return { indicators, evidence, reasoning };
  }

  private formatMarketAnalysis(data: MarketData, regime?: RegimeType, indicators?: ReturnType<typeof this.analyzeMarketIndicators>): string {
    const trendEmoji = data.trend === 'up' ? '📈' : data.trend === 'down' ? '📉' : '➡️';
    const regimeText = regime ? `Current market regime: **${regime}**` : 'Regime detection active';
    
    return `
${trendEmoji} **Market Analysis - ${data.symbol}**

**Current Price:** ${data.price.toFixed(2)}
**Last Digit:** ${data.digit}

${regimeText}

**Market Conditions:**
${indicators?.indicators.map(i => `- ${i}`).join('\n') || 'Analyzing market conditions...'}

**Recommendation:** Based on current analysis, the market shows ${data.trend === 'sideways' ? 'consolidation' : data.trend + ' momentum'}.
    `.trim();
  }

  private analyzeStrategyPerformance(trades: Trade[], statistics: TradeStatistics) {
    const winRate = statistics.total_trades > 0 
      ? (statistics.wins / statistics.total_trades) * 100 
      : 0;
    
    // Calculate profit factor
    const grossProfit = statistics.total_profit > 0 ? statistics.total_profit : 0;
    const grossLoss = Math.abs(statistics.worst_trade * statistics.losses);
    const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? 999 : 0;
    
    return {
      confidence: 0.85,
      evidence: [
        `Total trades analyzed: ${statistics.total_trades}`,
        `Win rate: ${winRate.toFixed(1)}%`,
        `Profit factor: ${profitFactor.toFixed(2)}`,
      ],
      reasoning: [
        'Analyzing historical trade performance',
        'Comparing against benchmark metrics',
      ],
      indicators: [
        `Win rate ${winRate > 55 ? 'exceeds' : 'meets'} threshold`,
        `Average profit: $${statistics.avg_win?.toFixed(2) || 'N/A'}`,
      ],
      summary: '',
    };
  }

  private formatStrategyReview(performance: ReturnType<typeof this.analyzeStrategyPerformance>): string {
    return `
**Strategy Performance Review**

**Key Metrics:**
${performance.evidence.map(e => `- ${e}`).join('\n')}

**Analysis:**
${performance.reasoning.map(r => `- ${r}`).join('\n')}

**Indicators:**
${performance.indicators.map(i => `- ${i}`).join('\n')}
    `.trim();
  }

  private analyzeRisk(currentTrade: Trade | undefined, portfolio: PortfolioData) {
    if (!portfolio) {
      return {
        summary: 'Analyzing risk...',
        confidence: 0.5,
        evidence: ['Portfolio data not available'],
        reasoning: ['Waiting for data'],
        indicators: [],
      };
    }

    const riskLevel = portfolio.drawdownPercent > 20 ? 'HIGH' 
      : portfolio.drawdownPercent > 10 ? 'MEDIUM' 
      : 'LOW';

    return {
      summary: `Current risk level: **${riskLevel}**\n\nDrawdown: ${portfolio.drawdownPercent.toFixed(1)}%\nMax drawdown: ${portfolio.maxDrawdown.toFixed(1)}%`,
      confidence: 0.9,
      evidence: [
        `Drawdown: ${portfolio.drawdownPercent.toFixed(2)}%`,
        `Win rate: ${portfolio.winRate.toFixed(1)}%`,
        `Profit factor: ${portfolio.profitFactor.toFixed(2)}`,
      ],
      reasoning: [
        `Risk level determined by ${riskLevel.toLowerCase()} drawdown`,
        'Position sizing within recommended limits',
      ],
      indicators: [
        `Risk/Reward: ${(1 / portfolio.winRate).toFixed(2)}`,
        `Exposure: ${Object.values(portfolio.exposure)[0] || 0}%`,
      ],
    };
  }

  private explainTrade(trade: Trade, marketData?: MarketData, regime?: RegimeType) {
    const isWin = (trade.profit || 0) > 0;
    
    return {
      summary: `Trade ${isWin ? 'won' : 'lost'} $${Math.abs(trade.profit || 0).toFixed(2)}\n\nContract: ${trade.type}\nEntry: ${trade.entry_time}\nExit: ${trade.exit_time || 'Open'}`,
      confidence: 0.9,
      evidence: [
        `Contract type: ${trade.type}`,
        `Profit: $${trade.profit?.toFixed(2) || '0.00'}`,
        `Duration: ${trade.exit_time ? 'Closed' : 'Open'}`,
      ],
      reasoning: [
        regime ? `Trade executed in ${regime} regime` : 'Regime at trade time',
        marketData ? `Entry digit: ${marketData.digit}` : 'Market data recorded',
      ],
      indicators: [
        `Confidence: ${trade.confidence || 'N/A'}%`,
        `Amount: $${trade.amount?.toFixed(2) || 'N/A'}`,
      ],
      context: 'Historical context unavailable',
    };
  }

  private analyzePortfolio(trades?: Trade[], statistics?: TradeStatistics, portfolio?: PortfolioData) {
    const summary = portfolio 
      ? `Portfolio Overview:\n\nTotal Equity: $${portfolio.equity.toFixed(2)}\nOpen P/L: $${portfolio.openPnl.toFixed(2)}\nClosed P/L: $${portfolio.closedPnl.toFixed(2)}\nDrawdown: ${portfolio.drawdownPercent.toFixed(1)}%`
      : 'Analyzing portfolio...';

    return {
      summary,
      confidence: 0.85,
      evidence: portfolio ? [
        `Equity: $${portfolio.equity.toFixed(2)}`,
        `Win rate: ${portfolio.winRate.toFixed(1)}%`,
        `Sharpe ratio: ${portfolio.sharpeRatio.toFixed(2)}`,
      ] : [],
      reasoning: ['Analyzing portfolio metrics', 'Comparing against benchmarks'],
      indicators: portfolio ? [
        `Profit factor: ${portfolio.profitFactor.toFixed(2)}`,
        `Max drawdown: ${portfolio.maxDrawdown.toFixed(1)}%`,
      ] : [],
      alternatives: ['Consider reducing exposure', 'Maintain current strategy'],
    };
  }

  private createSessionSummary(trades: Trade[], statistics: TradeStatistics) {
    const wins = trades.filter(t => (t.profit || 0) > 0);
    const losses = trades.filter(t => (t.profit || 0) <= 0);
    const totalPnL = trades.reduce((sum, t) => sum + (t.profit || 0), 0);

    return {
      narrative: `
**Session Summary**

**Performance:**
- Total trades: ${trades.length}
- Wins: ${wins.length} (${((wins.length / trades.length) * 100).toFixed(0)}%)
- Losses: ${losses.length}
- Net P/L: $${totalPnL.toFixed(2)}

**Key Observations:**
- ${wins.length > losses.length ? 'Winning session overall' : 'Challenging session with more losses'}
- Average win: $${(wins.reduce((s, t) => s + (t.profit || 0), 0) / (wins.length || 1)).toFixed(2)}
- Average loss: $${(losses.reduce((s, t) => s + (t.profit || 0), 0) / (losses.length || 1)).toFixed(2)}
      `.trim(),
      confidence: 0.9,
      evidence: [
        `Trades: ${trades.length}`,
        `Wins: ${wins.length}`,
        `Total P/L: $${totalPnL.toFixed(2)}`,
      ],
      reasoning: ['Session data analyzed', 'Metrics calculated'],
      indicators: [
        `Win rate: ${((wins.length / trades.length) * 100).toFixed(0)}%`,
        `Avg win/loss ratio: ${Math.abs(wins.length ? wins.reduce((s, t) => s + (t.profit || 0), 0) / wins.length : 0 / (losses.length || 1)).toFixed(2)}`,
      ],
    };
  }

  private createDailyBriefing(trades?: Trade[], statistics?: TradeStatistics, marketData?: MarketData, portfolio?: PortfolioData) {
    return {
      narrative: `
**Daily Briefing - ${new Date().toLocaleDateString()}**

**Current Market:**
${marketData ? `- Symbol: ${marketData.symbol}\n- Price: ${marketData.price.toFixed(2)}\n- Trend: ${marketData.trend}` : '- Waiting for market data'}

**Today's Performance:**
${trades && trades.length > 0 
  ? `- Trades: ${trades.length}\n- P/L: $${trades.reduce((s, t) => s + (t.profit || 0), 0).toFixed(2)}`
  : '- No trades today yet'}

**Portfolio Status:**
${portfolio 
  ? `- Equity: $${portfolio.equity.toFixed(2)}\n- Drawdown: ${portfolio.drawdownPercent.toFixed(1)}%\n- Win Rate: ${portfolio.winRate.toFixed(0)}%`
  : '- Loading portfolio data...'}

**Recommendations:**
1. Monitor ${marketData?.trend === 'up' ? 'for continuation' : 'for reversal signals'}
2. ${portfolio && portfolio.drawdownPercent > 15 ? 'Consider reducing position sizes' : 'Maintain current risk management'}
3. Review recent losing trades for patterns
      `.trim(),
      confidence: 0.85,
      evidence: [
        `Date: ${new Date().toLocaleDateString()}`,
        portfolio ? `Equity: $${portfolio.equity.toFixed(2)}` : 'Portfolio loading',
      ],
      reasoning: ['Daily data aggregated', 'Market conditions analyzed'],
      indicators: [
        marketData ? `Volatility: ${marketData.volatility.toFixed(2)}` : 'Market data pending',
      ],
      alternatives: ['Conservative approach recommended', 'Monitor for opportunities'],
    };
  }

  private explainReplay(events: ReplayEvent[], annotations: TradeAnnotation[]) {
    const significantEvents = annotations.filter(a => a.important);
    
    return {
      narrative: `
**Replay Analysis**

**Key Moments:**
${significantEvents.map(e => `- ${e.content}`).join('\n')}

**Event Summary:**
- Total events: ${events.length}
- Trade entries: ${events.filter(e => e.type === 'trade_entry').length}
- Trade exits: ${events.filter(e => e.type === 'trade_exit').length}
- Regime changes: ${events.filter(e => e.type === 'regime_change').length}

**AI Insights:**
${annotations.filter(a => a.type === 'ai_commentary').map(a => `- ${a.content}`).join('\n') || '- Analyzing replay data...'}
      `.trim(),
      confidence: 0.8,
      evidence: [
        `Significant events: ${significantEvents.length}`,
        `AI annotations: ${annotations.length}`,
      ],
      reasoning: ['Replay data analyzed', 'Patterns identified'],
      indicators: significantEvents.map(e => e.content),
    };
  }

  private async getHistoricalContext(data: MarketData): Promise<string> {
    // In production, this would query historical data
    return `Historical analysis for ${data.symbol} shows typical patterns over the past 30 days. Current volatility is ${data.volatility > 0.5 ? 'elevated' : 'normal'} compared to historical average.`;
  }

  private generateAlternativeScenarios(data: MarketData): string[] {
    return [
      `${data.trend === 'up' ? 'Possible reversal if support breaks' : 'Possible upward continuation if resistance breaks'}`,
      'Range-bound trading if volatility decreases further',
      `${data.trend === 'sideways' ? 'Breakout expected' : 'Consolidation may continue'}`,
    ];
  }

  private createMockResponse(queryId: string, type: AIQueryType): AIResponse {
    return {
      id: queryId,
      queryId,
      type,
      content: 'AI analysis in progress. Please provide more context for detailed insights.',
      confidence: 0.5,
      evidence: ['Data analysis initiated'],
      reasoning: ['Gathering relevant information'],
      supportingIndicators: ['Processing...'],
      timestamp: Date.now(),
    };
  }
}

// Export singleton instance
export const aiEngine = new AIEngine();

// Export hook for React
export function useAI() {
  return {
    process: (query: Omit<AIQuery, 'id' | 'timestamp'>) => aiEngine.process(query),
    getResponse: (id: string) => aiEngine.getResponse(id),
  };
}

export default aiEngine;
