from typing import Dict, Any, Optional
from models import Prediction
from backtesting.strategy import BacktestStrategy


class GridStrategy(BacktestStrategy):
    """Grid trading strategy - places trades at regular price intervals"""
    
    def __init__(self, grid_size: float = 0.001, max_positions: int = 5):
        super().__init__("grid")
        self.grid_size = grid_size
        self.max_positions = max_positions
        self.grid_levels = []
        self.last_price = None
    
    def generate_signal(self, data: Dict[str, Any]) -> Optional[Prediction]:
        """Generate signal based on grid levels"""
        current_price = data.get("current_price", 0)
        
        if self.last_price is None:
            self.last_price = current_price
            self._initialize_grid(current_price)
            return None
        
        # Check if price crossed a grid level
        for level in self.grid_levels:
            if (self.last_price < level <= current_price) or (self.last_price > level >= current_price):
                # Price crossed grid level - place trade
                direction = "CALL" if current_price > self.last_price else "PUT"
                
                return Prediction(
                    type="GRID",
                    direction=direction,
                    confidence=60,
                    reason=f"Grid level crossed at {level}"
                )
        
        self.last_price = current_price
        return None
    
    def _initialize_grid(self, price: float):
        """Initialize grid levels around current price"""
        self.grid_levels = []
        for i in range(-self.max_positions, self.max_positions + 1):
            if i != 0:
                self.grid_levels.append(price + (i * self.grid_size))
