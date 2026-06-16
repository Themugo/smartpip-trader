from typing import Dict, Any, Optional, List
from datetime import datetime
from .multi_market_analyzer import MultiMarketAnalyzer


class MarketSelector:
    """Selects the best market for trading based on analysis"""
    
    def __init__(self):
        self.multi_market_analyzer = MultiMarketAnalyzer()
        self.current_market = "R_100"
        self.last_switch_time = None
        self.min_switch_interval = 300  # 5 minutes minimum between switches
        self.switch_count = 0
        self.market_history = []
    
    def evaluate_markets(self) -> Dict[str, Any]:
        """Evaluate all markets and select the best one"""
        analysis = self.multi_market_analyzer.analyze_all_markets()
        
        best_market = analysis.get("best_market")
        best_score = analysis.get("best_score", 0)
        
        # Determine if we should switch markets
        should_switch = self._should_switch_market(best_market, best_score)
        
        if should_switch and best_market:
            self._switch_market(best_market)
        
        return {
            "current_market": self.current_market,
            "best_market": best_market,
            "best_score": best_score,
            "should_switch": should_switch,
            "all_scores": analysis.get("all_scores", {}),
            "market_details": analysis.get("market_details", {}),
            "switch_count": self.switch_count
        }
    
    def _should_switch_market(self, best_market: str, best_score: float) -> bool:
        """Determine if we should switch to the best market"""
        if not best_market:
            return False
        
        # Don't switch if already on best market
        if best_market == self.current_market:
            return False
        
        # Check minimum switch interval
        if self.last_switch_time:
            time_since_switch = (datetime.now() - self.last_switch_time).total_seconds()
            if time_since_switch < self.min_switch_interval:
                return False
        
        # Get current market score
        current_score = self.multi_market_analyzer.markets.get(self.current_market, {}).get("score", 0)
        
        # Only switch if best market is significantly better (10% improvement)
        score_improvement = (best_score - current_score) / current_score if current_score > 0 else 0
        
        if score_improvement > 0.10:
            return True
        
        # Also switch if current market score is below threshold
        if current_score < 50 and best_score > 70:
            return True
        
        return False
    
    def _switch_market(self, new_market: str):
        """Switch to a new market"""
        old_market = self.current_market
        self.current_market = new_market
        self.last_switch_time = datetime.now()
        self.switch_count += 1
        
        # Record in history
        self.market_history.append({
            "from": old_market,
            "to": new_market,
            "timestamp": datetime.now().isoformat(),
            "reason": "Better opportunity"
        })
        
        if len(self.market_history) > 100:
            self.market_history = self.market_history[-100:]
    
    def add_tick(self, market: str, price: float, digits: List[int]):
        """Add tick data for a market"""
        self.multi_market_analyzer.add_tick(market, price, digits)
    
    def record_trade_result(self, market: str, profit: float):
        """Record trade result for a market"""
        self.multi_market_analyzer.record_trade_result(market, profit)
    
    def get_current_market(self) -> str:
        """Get the current selected market"""
        return self.current_market
    
    def get_market_ranking(self) -> List[tuple]:
        """Get markets ranked by score"""
        return self.multi_market_analyzer.get_market_ranking()
    
    def get_switch_history(self) -> List[Dict[str, Any]]:
        """Get history of market switches"""
        return self.market_history
    
    def force_switch(self, market: str):
        """Force switch to a specific market"""
        if market in self.multi_market_analyzer.markets:
            self._switch_market(market)
