from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import deque
from .strategy import BacktestStrategy
from analysis import AnalysisManager
from indicators import TechnicalIndicatorManager


class Backtester:
    """Backtesting engine for testing trading strategies on historical data"""
    
    def __init__(self):
        self.strategies = {}
        self.analysis_manager = AnalysisManager()
        self.indicator_manager = TechnicalIndicatorManager()
    
    def add_strategy(self, strategy: BacktestStrategy):
        """Add a backtesting strategy"""
        self.strategies[strategy.name] = strategy
    
    def run_backtest(self, historical_data: List[Dict[str, Any]], strategy_name: str) -> Dict[str, Any]:
        """
        Run backtest on historical data
        
        Args:
            historical_data: List of historical price data points
            strategy_name: Name of strategy to test
            
        Returns:
            Backtest results and statistics
        """
        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy {strategy_name} not found")
        
        strategy = self.strategies[strategy_name]
        strategy.reset()
        
        price_history = deque(maxlen=500)
        last_20_digits = []
        
        for data_point in historical_data:
            price = data_point.get("price")
            timestamp = data_point.get("timestamp")
            
            if not price:
                continue
            
            price_history.append(price)
            
            # Extract last digit
            price_str = f"{price:.4f}"
            last_digit = int(price_str[-1]) if price_str[-1].isdigit() else 0
            last_20_digits.append(last_digit)
            if len(last_20_digits) > 20:
                last_20_digits = last_20_digits[-20:]
            
            # Prepare analysis data
            analysis_data = {
                "last_20_digits": last_20_digits,
                "price_history": price_history,
                "current_price": price,
                "market": data_point.get("market", "R_100"),
                "markets": {}
            }
            
            # Generate signal from strategy
            prediction = strategy.generate_signal(analysis_data)
            
            if prediction and prediction.confidence > 50:
                # Execute trade
                strategy.execute_trade(prediction, price)
                
                # Simulate trade closure after 1 tick (simplified)
                # In real backtesting, you'd use actual trade duration
                if strategy.trades:
                    last_trade = strategy.trades[-1]
                    if last_trade["exit_price"] is None:
                        # Close trade after next price point
                        pass
        
        # Close all open trades at end
        for trade in strategy.trades:
            if trade["exit_price"] is None and historical_data:
                trade["exit_price"] = historical_data[-1].get("price", trade["entry_price"])
                trade["exit_time"] = datetime.now().isoformat()
                if trade["direction"] == "CALL":
                    profit = (trade["exit_price"] - trade["entry_price"]) * 100 * trade["amount"]
                elif trade["direction"] == "PUT":
                    profit = (trade["entry_price"] - trade["exit_price"]) * 100 * trade["amount"]
                else:
                    profit = 0
                trade["profit"] = profit
                strategy.balance += profit
        
        return strategy.get_statistics()
    
    def run_multi_strategy_backtest(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Run backtest on all strategies"""
        results = {}
        
        for strategy_name in self.strategies:
            try:
                results[strategy_name] = self.run_backtest(historical_data, strategy_name)
            except Exception as e:
                results[strategy_name] = {"error": str(e)}
        
        return results
    
    def compare_strategies(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare all strategies and return ranking"""
        results = self.run_multi_strategy_backtest(historical_data)
        
        # Rank strategies by ROI
        ranked = sorted(
            [(name, stats) for name, stats in results.items() if "error" not in stats],
            key=lambda x: x[1].get("roi", 0),
            reverse=True
        )
        
        return {
            "rankings": ranked,
            "best_strategy": ranked[0][0] if ranked else None,
            "detailed_results": results
        }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable backtest report"""
        report = []
        report.append("=" * 60)
        report.append("BACKTEST REPORT")
        report.append("=" * 60)
        
        for strategy_name, stats in results.items():
            if "error" in stats:
                report.append(f"\n{strategy_name}: ERROR - {stats['error']}")
                continue
            
            report.append(f"\n{strategy_name}:")
            report.append(f"  Total Trades: {stats['total_trades']}")
            report.append(f"  Win Rate: {stats['win_rate']:.2f}%")
            report.append(f"  Total Profit: ${stats['total_profit']:.2f}")
            report.append(f"  ROI: {stats['roi']:.2f}%")
            report.append(f"  Max Drawdown: {stats['max_drawdown']:.2f}%")
            report.append(f"  Final Balance: ${stats['final_balance']:.2f}")
        
        report.append("\n" + "=" * 60)
        return "\n".join(report)
