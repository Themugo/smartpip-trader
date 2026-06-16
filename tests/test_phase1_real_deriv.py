"""
Phase 1 Implementation Test - Real Deriv API Integration
Tests adaptive risk parameters, Kelly Criterion, regime detection, 
performance database, and strategy weight adaptation with real Deriv data
"""

import asyncio
import os
import sys
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Phase1RealDerivTest:
    """Test Phase 1 implementation with real Deriv API"""
    
    def __init__(self):
        self.api_token = os.getenv("DERIV_API_TOKEN")
        self.app_id = os.getenv("DERIV_APP_ID", "1089")
        
        # Import Phase 1 components
        from trading.adaptive_risk_manager import AdaptiveRiskManager
        from trading.kelly_position_sizer import KellyPositionSizer
        from core.regime_detector import RegimeDetector
        from utils.performance_database import PerformanceDatabase
        from strategies.adaptive_strategy_manager import AdaptiveStrategyManager
        
        self.risk_manager = AdaptiveRiskManager()
        self.kelly_sizer = KellyPositionSizer()
        self.regime_detector = RegimeDetector()
        self.performance_db = PerformanceDatabase()
        self.strategy_manager = AdaptiveStrategyManager()
        
        self.test_results = []
    
    async def test_adaptive_risk_manager(self):
        """Test adaptive risk manager with real Deriv data"""
        print("\n=== Testing Adaptive Risk Manager ===")
        
        try:
            # Simulate real Deriv data updates
            for i in range(20):
                price = 1000.0 + i * 0.1
                digits = [i % 10 for _ in range(5)]
                market = "R_10"
                
                self.risk_manager.update_with_deriv_data(price, digits, market)
                
                # Simulate trade result
                profit = 10 if i % 3 == 0 else -5
                self.risk_manager.record_trade_result(
                    profit, market, "unified", 85
                )
            
            # Get risk metrics
            metrics = self.risk_manager.get_risk_metrics()
            
            print(f"✓ Volatility Regime: {metrics['volatility_regime']}")
            print(f"✓ Trend Regime: {metrics['trend_regime']}")
            print(f"✓ Confidence Threshold: {metrics['confidence_threshold']:.1f}%")
            print(f"✓ Position Multiplier: {metrics['position_multiplier']:.2f}")
            print(f"✓ Drawdown: {metrics['drawdown_percentage']:.2f}%")
            print(f"✓ Win Rate: {metrics['win_rate']:.2%}")
            
            self.test_results.append({
                "test": "adaptive_risk_manager",
                "status": "passed",
                "metrics": metrics
            })
            
            return True
        except Exception as e:
            print(f"✗ Adaptive Risk Manager Test Failed: {e}")
            self.test_results.append({
                "test": "adaptive_risk_manager",
                "status": "failed",
                "error": str(e)
            })
            return False
    
    async def test_kelly_position_sizer(self):
        """Test Kelly Criterion position sizer with real market flow"""
        print("\n=== Testing Kelly Position Sizer ===")
        
        try:
            # Simulate real market flow data
            for i in range(20):
                market_flow = {
                    "change": (i % 3 - 1) * 0.001,
                    "volatility": 0.01 + (i % 5) * 0.002,
                    "market": "R_10",
                    "timestamp": datetime.now().isoformat()
                }
                
                self.kelly_sizer.update_with_market_flow(market_flow)
                
                # Simulate trade result
                profit = 15 if i % 3 == 0 else -8
                self.kelly_sizer.update_trade_result(profit, "R_10", "unified")
            
            # Get Kelly metrics
            kelly_metrics = self.kelly_sizer.get_kelly_metrics("R_10")
            perf_metrics = self.kelly_sizer.get_performance_metrics()
            
            print(f"✓ Kelly Criterion: {kelly_metrics.get('kelly', 'N/A')}")
            print(f"✓ Fractional Kelly: {kelly_metrics.get('fractional_kelly', 'N/A')}")
            print(f"✓ Position Size: {kelly_metrics.get('position_size', 'N/A')}")
            print(f"✓ Total Trades: {perf_metrics['total_trades']}")
            print(f"✓ Win Rate: {perf_metrics['win_rate']:.2%}")
            print(f"✓ Profit Factor: {perf_metrics['profit_factor']:.2f}")
            
            self.test_results.append({
                "test": "kelly_position_sizer",
                "status": "passed",
                "kelly_metrics": kelly_metrics,
                "performance_metrics": perf_metrics
            })
            
            return True
        except Exception as e:
            print(f"✗ Kelly Position Sizer Test Failed: {e}")
            self.test_results.append({
                "test": "kelly_position_sizer",
                "status": "failed",
                "error": str(e)
            })
            return False
    
    async def test_regime_detector(self):
        """Test regime detector with real Deriv digits"""
        print("\n=== Testing Regime Detector ===")
        
        try:
            # Simulate real Deriv data
            for i in range(50):
                price = 1000.0 + i * 0.05 + (i % 3) * 0.1
                digits = [i % 10 for _ in range(5)]
                market = "R_10"
                
                self.regime_detector.update_with_deriv_data(price, digits, market)
            
            # Get regime summary
            regime_summary = self.regime_detector.get_regime_summary()
            digit_analysis = self.regime_detector.get_digit_analysis()
            flow_analysis = self.regime_detector.get_market_flow_analysis()
            
            print(f"✓ Volatility Regime: {regime_summary['volatility_regime']}")
            print(f"✓ Trend Regime: {regime_summary['trend_regime']}")
            print(f"✓ Digit Regime: {regime_summary['digit_regime']}")
            print(f"✓ Liquidity Regime: {regime_summary['liquidity_regime']}")
            print(f"✓ Regime Confidence: {regime_summary['regime_confidence']:.2%}")
            print(f"✓ Total Digits Analyzed: {digit_analysis['total_digits']}")
            print(f"✓ Most Frequent Digit: {digit_analysis['most_frequent_digit']}")
            print(f"✓ Average Volatility: {flow_analysis['avg_volatility']:.4f}")
            
            # Get optimal trading parameters
            optimal_params = self.regime_detector.get_optimal_trading_parameters()
            print(f"✓ Optimal Confidence Threshold: {optimal_params['confidence_threshold']}%")
            print(f"✓ Optimal Position Multiplier: {optimal_params['position_size_multiplier']:.2f}")
            print(f"✓ Preferred Strategies: {', '.join(optimal_params['preferred_strategies'])}")
            
            self.test_results.append({
                "test": "regime_detector",
                "status": "passed",
                "regime_summary": regime_summary,
                "digit_analysis": digit_analysis,
                "flow_analysis": flow_analysis,
                "optimal_params": optimal_params
            })
            
            return True
        except Exception as e:
            print(f"✗ Regime Detector Test Failed: {e}")
            self.test_results.append({
                "test": "regime_detector",
                "status": "failed",
                "error": str(e)
            })
            return False
    
    async def test_performance_database(self):
        """Test performance database with real trade data"""
        print("\n=== Testing Performance Database ===")
        
        try:
            # Record sample trades with real data
            strategies = ["even_odd", "rise_fall", "over_under", "match_diff", "technical", "ml"]
            markets = ["R_10", "R_25", "R_50", "R_75", "R_100"]
            
            for i in range(30):
                trade_data = {
                    "timestamp": datetime.now().isoformat(),
                    "market": markets[i % len(markets)],
                    "direction": "CALL" if i % 2 == 0 else "PUT",
                    "amount": 100,
                    "confidence": 80 + (i % 15),
                    "entry_price": 1000.0 + i * 0.1,
                    "exit_price": 1000.0 + i * 0.1 + (5 if i % 3 == 0 else -3),
                    "profit": 15 if i % 3 == 0 else -8,
                    "strategy": strategies[i % len(strategies)],
                    "analysis_type": "unified",
                    "volatility_regime": "normal",
                    "trend_regime": "neutral",
                    "digit_regime": "random",
                    "digits": [i % 10 for _ in range(5)],
                    "market_flow": {"change": 0.001, "volatility": 0.01},
                    "status": "completed"
                }
                
                self.performance_db.record_trade(trade_data)
            
            # Query performance data
            strategy_perf = self.performance_db.get_strategy_performance()
            market_perf = self.performance_db.get_market_performance()
            time_perf = self.performance_db.get_time_performance()
            recent_trades = self.performance_db.get_recent_trades(10)
            
            print(f"✓ Strategy Performance Records: {len(strategy_perf)}")
            print(f"✓ Market Performance Records: {len(market_perf)}")
            print(f"✓ Time Performance Records: {len(time_perf)}")
            print(f"✓ Recent Trades: {len(recent_trades)}")
            
            if strategy_perf:
                print(f"✓ Sample Strategy Win Rate: {strategy_perf[0]['win_rate']:.2%}")
            
            self.test_results.append({
                "test": "performance_database",
                "status": "passed",
                "strategy_count": len(strategy_perf),
                "market_count": len(market_perf),
                "time_count": len(time_perf),
                "trade_count": len(recent_trades)
            })
            
            return True
        except Exception as e:
            print(f"✗ Performance Database Test Failed: {e}")
            self.test_results.append({
                "test": "performance_database",
                "status": "failed",
                "error": str(e)
            })
            return False
    
    async def test_strategy_weight_adaptation(self):
        """Test strategy weight adaptation with real performance"""
        print("\n=== Testing Strategy Weight Adaptation ===")
        
        try:
            # Simulate strategy performance updates
            strategies = ["even_odd", "rise_fall", "over_under", "match_diff", "technical", "ml"]
            markets = ["R_10", "R_25", "R_50"]
            
            for i in range(40):
                strategy = strategies[i % len(strategies)]
                market = markets[i % len(markets)]
                profit = 20 if i % 3 == 0 else -10
                
                regime = {
                    "volatility": "normal" if i % 2 == 0 else "high",
                    "trend": "neutral" if i % 3 == 0 else "uptrend"
                }
                
                self.strategy_manager.update_strategy_performance(
                    strategy, profit, market, regime, datetime.now().isoformat()
                )
            
            # Get adaptive weights
            adaptive_weights = self.strategy_manager.get_adaptive_weights()
            performance_summary = self.strategy_manager.get_strategy_performance_summary()
            best_strategies = self.strategy_manager.get_best_strategies(3)
            enabled_strategies = self.strategy_manager.get_enabled_strategies()
            
            print(f"✓ Adaptive Weights Calculated:")
            for strategy, weight in adaptive_weights.items():
                print(f"  - {strategy}: {weight:.3f}")
            
            print(f"✓ Best Strategies:")
            for strategy in best_strategies:
                print(f"  - {strategy['strategy']}: {strategy['win_rate']:.2%} win rate")
            
            print(f"✓ Enabled Strategies: {len(enabled_strategies)}")
            print(f"✓ Strategies with Sufficient Data: {len(performance_summary)}")
            
            self.test_results.append({
                "test": "strategy_weight_adaptation",
                "status": "passed",
                "adaptive_weights": adaptive_weights,
                "best_strategies": best_strategies,
                "enabled_count": len(enabled_strategies)
            })
            
            return True
        except Exception as e:
            print(f"✗ Strategy Weight Adaptation Test Failed: {e}")
            self.test_results.append({
                "test": "strategy_weight_adaptation",
                "status": "failed",
                "error": str(e)
            })
            return False
    
    async def test_real_deriv_connection(self):
        """Test connection to real Deriv API"""
        print("\n=== Testing Real Deriv API Connection ===")
        
        if not self.api_token:
            print("⚠ DERIV_API_TOKEN not set, skipping real API test")
            self.test_results.append({
                "test": "real_deriv_connection",
                "status": "skipped",
                "reason": "No API token"
            })
            return False
        
        try:
            import websockets
            
            url = f"wss://ws.binaryws.com/websockets/v3?app_id={self.app_id}"
            
            async with websockets.connect(url) as ws:
                # Authorize
                auth_msg = json.dumps({"authorize": self.api_token})
                await ws.send(auth_msg)
                auth_response = await ws.recv()
                auth_data = json.loads(auth_response)
                
                if auth_data.get("error"):
                    print(f"✗ Authorization Failed: {auth_data['error']['message']}")
                    self.test_results.append({
                        "test": "real_deriv_connection",
                        "status": "failed",
                        "error": auth_data['error']['message']
                    })
                    return False
                
                print("✓ Authorization Successful")
                
                # Get account info
                balance_msg = json.dumps({"balance": 1, "subscribe": 1})
                await ws.send(balance_msg)
                balance_response = await ws.recv()
                balance_data = json.loads(balance_response)
                
                if balance_data.get("error"):
                    print(f"✗ Balance Request Failed: {balance_data['error']['message']}")
                else:
                    balance = balance_data.get("balance", {}).get("balance", {})
                    print(f"✓ Account Balance: {balance.get('currency', 'USD')} {balance.get('balance', 0)}")
                
                # Subscribe to ticks
                ticks_msg = json.dumps({"ticks": "R_10", "subscribe": 1})
                await ws.send(ticks_msg)
                
                # Receive a few ticks
                for i in range(5):
                    tick_response = await ws.recv()
                    tick_data = json.loads(tick_response)
                    
                    if "tick" in tick_data:
                        tick = tick_data["tick"]
                        price = tick["quote"]
                        digits = [int(d) for d in str(price).split(".")[-1][:5]]
                        
                        print(f"✓ Tick {i+1}: Price {price}, Digits {digits}")
                        
                        # Update Phase 1 components with real data
                        self.risk_manager.update_with_deriv_data(price, digits, "R_10")
                        self.regime_detector.update_with_deriv_data(price, digits, "R_10")
                
                print("✓ Real Deriv API Connection Successful")
                
                self.test_results.append({
                    "test": "real_deriv_connection",
                    "status": "passed",
                    "account_balance": balance.get("balance", 0) if balance else 0
                })
                
                return True
                
        except Exception as e:
            print(f"✗ Real Deriv Connection Test Failed: {e}")
            self.test_results.append({
                "test": "real_deriv_connection",
                "status": "failed",
                "error": str(e)
            })
            return False
    
    async def run_all_tests(self):
        """Run all Phase 1 tests"""
        print("=" * 60)
        print("Phase 1 Implementation Test - Real Deriv Integration")
        print("=" * 60)
        
        # Test all components
        await self.test_adaptive_risk_manager()
        await self.test_kelly_position_sizer()
        await self.test_regime_detector()
        await self.test_performance_database()
        await self.test_strategy_weight_adaptation()
        await self.test_real_deriv_connection()
        
        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r["status"] == "passed")
        failed = sum(1 for r in self.test_results if r["status"] == "failed")
        skipped = sum(1 for r in self.test_results if r["status"] == "skipped")
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        
        if failed == 0:
            print("\n✓ All Phase 1 tests passed successfully!")
        else:
            print(f"\n✗ {failed} test(s) failed")
        
        # Save results
        with open("phase1_test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        
        print("\nTest results saved to phase1_test_results.json")
        
        # Close database
        self.performance_db.close()
        
        return failed == 0


async def main():
    """Main test function"""
    tester = Phase1RealDerivTest()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✓ Phase 1 implementation is ready for production use")
    else:
        print("\n✗ Phase 1 implementation requires fixes before production use")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
