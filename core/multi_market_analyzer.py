from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict, deque
import numpy as np
from analysis import AnalysisManager, AdaptiveConfidence


class MultiMarketAnalyzer:
    """Analyze multiple markets and select the best trading opportunity"""
    
    def __init__(self):
        self.markets = {
            # Volatility indices (tick-based)
            "R_10": {"name": "Volatility 10", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "tick"},
            "R_25": {"name": "Volatility 25", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "tick"},
            "R_50": {"name": "Volatility 50", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "tick"},
            "R_75": {"name": "Volatility 75", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "tick"},
            "R_100": {"name": "Volatility 100", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "tick"},
            # Short-duration markets (10s, 25s, etc.)
            "R_10_10S": {"name": "Volatility 10 10s", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "short"},
            "R_25_10S": {"name": "Volatility 25 10s", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "short"},
            "R_50_10S": {"name": "Volatility 50 10s", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "short"},
            "R_75_10S": {"name": "Volatility 75 10s", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "short"},
            "R_100_10S": {"name": "Volatility 100 10s", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "short"},
            # Additional short durations
            "R_100_25S": {"name": "Volatility 100 25s", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "short"},
            "R_100_50S": {"name": "Volatility 100 50s", "data": deque(maxlen=500), "analysis": None, "score": 0, "type": "short"},
        }
        self.analysis_manager = AnalysisManager()
        self.adaptive_confidence = AdaptiveConfidence(base_threshold=70)
        self.best_market = None
        self.market_scores = {}
        self.historical_performance = defaultdict(list)
    
    def add_tick(self, market: str, price: float, digits: List[int]):
        """Add tick data for a market"""
        if market in self.markets:
            self.markets[market]["data"].append({
                "price": price,
                "digits": digits,
                "timestamp": datetime.now().isoformat()
            })
    
    def analyze_all_markets(self) -> Dict[str, Any]:
        """Analyze all markets and return scores"""
        results = {}
        
        for market, market_data in self.markets.items():
            if len(market_data["data"]) < 30:
                continue
            
            # Prepare analysis data
            price_history = [d["price"] for d in market_data["data"]]
            last_20_digits = []
            for d in list(market_data["data"])[-20:]:
                last_20_digits.extend(d["digits"][-1:])
                if len(last_20_digits) >= 20:
                    break
            last_20_digits = last_20_digits[-20:]
            
            analysis_data = {
                "last_20_digits": last_20_digits,
                "price_history": price_history,
                "current_price": price_history[-1],
                "market": market
            }
            
            # Run analysis
            analysis_result = self.analysis_manager.get_comprehensive_analysis(analysis_data)
            market_data["analysis"] = analysis_result
            
            # Calculate market score
            score = self._calculate_market_score(market, analysis_result, price_history)
            market_data["score"] = score
            results[market] = score
        
        # Select best market
        self.market_scores = results
        self.best_market = max(results.items(), key=lambda x: x[1]) if results else None
        
        return {
            "best_market": self.best_market[0] if self.best_market else None,
            "best_score": self.best_market[1] if self.best_market else 0,
            "all_scores": results,
            "market_details": self._get_market_details()
        }
    
    def _calculate_market_score(self, market: str, analysis: Dict[str, Any], price_history: List[float]) -> float:
        """Calculate composite score for a market"""
        score = 0.0
        
        # 1. Confidence score (0-30 points)
        best_prediction = analysis.get("best_prediction")
        if best_prediction:
            confidence = best_prediction.get("confidence", 0)
            score += (confidence / 100) * 30
        
        # 2. Volatility score (0-20 points) - optimal volatility is preferred
        if len(price_history) >= 20:
            returns = np.diff(price_history[-20:])
            volatility = np.std(returns) / np.mean(returns) if np.mean(returns) != 0 else 0
            # Optimal volatility range: 0.01 - 0.03
            if 0.01 <= volatility <= 0.03:
                score += 20
            elif 0.005 <= volatility <= 0.05:
                score += 15
            elif volatility > 0:
                score += 10
        
        # 3. Trend strength score (0-15 points)
        if len(price_history) >= 20:
            sma_10 = sum(price_history[-10:]) / 10
            sma_20 = sum(price_history[-20:]) / 20
            trend_strength = abs(sma_10 - sma_20) / sma_20 if sma_20 != 0 else 0
            score += min(trend_strength * 500, 15)
        
        # 4. Signal agreement score (0-20 points)
        signals = analysis.get("signals", [])
        if signals:
            bullish = sum(1 for s in signals if s.get("direction") == "CALL")
            bearish = sum(1 for s in signals if s.get("direction") == "PUT")
            agreement = max(bullish, bearish) / len(signals) if signals else 0
            score += agreement * 20
        
        # 5. Historical performance score (0-15 points)
        if market in self.historical_performance and self.historical_performance[market]:
            recent_performance = self.historical_performance[market][-10:]
            win_rate = sum(1 for p in recent_performance if p > 0) / len(recent_performance)
            score += win_rate * 15
        
        return min(score, 100)
    
    def _get_market_details(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information for all markets"""
        details = {}
        
        for market, market_data in self.markets.items():
            details[market] = {
                "name": market_data["name"],
                "score": market_data["score"],
                "data_points": len(market_data["data"]),
                "analysis": market_data["analysis"],
                "current_price": market_data["data"][-1]["price"] if market_data["data"] else None
            }
        
        return details
    
    def get_best_market(self) -> Optional[str]:
        """Get the best market to trade"""
        return self.best_market[0] if self.best_market else None
    
    def record_trade_result(self, market: str, profit: float):
        """Record trade result for a market"""
        self.historical_performance[market].append(profit)
        if len(self.historical_performance[market]) > 50:
            self.historical_performance[market] = self.historical_performance[market][-50:]
    
    def get_market_ranking(self) -> List[tuple]:
        """Get markets ranked by score"""
        return sorted(self.market_scores.items(), key=lambda x: x[1], reverse=True)
    
    def get_market_comparison(self) -> Dict[str, Any]:
        """Get comparison of all markets"""
        ranking = self.get_market_ranking()
        
        return {
            "ranking": ranking,
            "best": ranking[0] if ranking else None,
            "worst": ranking[-1] if ranking else None,
            "average_score": np.mean([s for _, s in ranking]) if ranking else 0,
            "score_spread": ranking[0][1] - ranking[-1][1] if len(ranking) > 1 else 0
        }
