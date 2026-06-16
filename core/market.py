import logging
from typing import Dict, Optional
from models import MarketType

logger = logging.getLogger(__name__)


class MarketManager:
    """Manages market definitions and selection"""
    
    def __init__(self):
        self.markets = {
            "R_10": {"type": MarketType.VOLATILITY, "volatility": "low", "spread": 0.001},
            "R_25": {"type": MarketType.VOLATILITY, "volatility": "medium", "spread": 0.002},
            "R_50": {"type": MarketType.VOLATILITY, "volatility": "high", "spread": 0.003},
            "R_75": {"type": MarketType.VOLATILITY, "volatility": "very_high", "spread": 0.004},
            "R_100": {"type": MarketType.VOLATILITY, "volatility": "extreme", "spread": 0.005},
            "1HZ10V": {"type": MarketType.VOLATILITY, "volatility": "synthetic", "spread": 0.001}
        }
        self.current_market = "R_100"
        self.market_scores = {}
        self.best_market = None
    
    def set_market(self, market: str):
        """Set current market"""
        if market in self.markets:
            self.current_market = market
    
    def get_current_market(self) -> str:
        """Get current market"""
        return self.current_market
    
    def get_market_info(self, market: str) -> Optional[Dict]:
        """Get market information"""
        return self.markets.get(market)
    
    def analyze_markets(self) -> str:
        """Analyze all markets and find best opportunity"""
        market_scores = {}
        
        for market, data in self.markets.items():
            score = 50
            
            # Higher score for higher volatility (more movement)
            vol_scores = {"low": 40, "medium": 60, "high": 70, "very_high": 80, "extreme": 85, "synthetic": 50}
            score += vol_scores.get(data["volatility"], 50)
            
            # Adjust based on spread
            score -= data["spread"] * 1000
            
            market_scores[market] = min(max(score, 0), 100)
        
        self.market_scores = market_scores
        self.best_market = max(market_scores, key=market_scores.get)
        
        return self.best_market
    
    def get_all_markets(self) -> Dict:
        """Get all markets"""
        return self.markets
    
    async def subscribe_to_market(self, websocket, market: str):
        """Subscribe to market ticks"""
        import json
        await websocket.send(json.dumps({"ticks": market, "subscribe": 1}))
        logger.info(f"Subscribed to {market}")
