import logging
from typing import Dict, Optional, Any
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
    
    async def discover_markets(self, connection) -> Dict[str, Dict[str, Any]]:
        """Discover currently active symbols from Deriv instead of relying on a stale hardcoded list."""
        response = await connection.request({"active_symbols": "brief", "product_type": "basic"})
        if response.get("error"):
            raise RuntimeError(response["error"].get("message", "active_symbols failed"))
        discovered = {}
        for item in response.get("active_symbols", []):
            symbol = item.get("underlying_symbol") or item.get("symbol")
            if not symbol:
                continue
            # Keep only synthetic/derived instruments suitable for this application.
            market_name = str(item.get("market_display_name") or "").lower()
            market_category = str(item.get("market") or "").lower()
            if "synthetic" not in market_category and "derived" not in market_category and "volatility" not in market_name and "crash" not in market_name and "boom" not in market_name and "range" not in market_name:
                continue
            existing = self.markets.get(symbol, {})
            discovered[symbol] = {
                **existing,
                "display_name": item.get("display_name") or symbol,
                "market": item.get("market"),
                "market_display_name": item.get("market_display_name"),
                "exchange_is_open": item.get("exchange_is_open"),
                "pip": item.get("pip"),
                "status": item.get("exchange_is_open"),
            }
        if discovered:
            self.markets = discovered
            if self.current_market not in self.markets:
                self.current_market = next(iter(self.markets))
        return self.markets

    async def subscribe_to_market(self, connection, market: str):
        """Subscribe through the shared connection owner."""
        await connection.request({"ticks": market, "subscribe": 1})
        logger.info("Subscribed to %s", market)
