import asyncio
import json
import time
from typing import Dict, Any, List
from datetime import datetime
from core import DerivAPI, MultiMarketAnalyzer, MarketSelector
from analysis import AnalysisManager
from trading import TradeExecutor, RiskManager, PositionSizer
from strategies import SniperStrategy, HFTStrategy
from backtesting import Backtester


class DerivFullTest:
    """Comprehensive test suite for all Deriv markets and analysis types"""
    
    def __init__(self, api_token: str):
        self.api = DerivAPI(api_token=api_token)
        self.multi_market_analyzer = MultiMarketAnalyzer()
        self.market_selector = MarketSelector()
        self.analysis_manager = AnalysisManager()
        self.trade_executor = TradeExecutor()
        self.risk_manager = RiskManager()
        self.position_sizer = PositionSizer()
        self.test_results = {}
        self.market_data = {}
    
    async def run_full_test(self) -> Dict[str, Any]:
        """Run comprehensive test on all markets and analysis types"""
        print("🚀 Starting Full Deriv Test Suite...")
        
        # Connect to Deriv API
        await self.api.connect()
        print("✅ Connected to Deriv API")
        
        # Test all markets
        markets = ["R_10", "R_25", "R_50", "R_75", "R_100", "R_100_10S", "R_100_25S"]
        
        for market in markets:
            print(f"\n📊 Testing market: {market}")
            result = await self.test_market(market)
            self.test_results[market] = result
        
        # Test all analysis types
        print(f"\n🔬 Testing all analysis types...")
        analysis_results = await self.test_all_analysis_types()
        
        # Test zero-loss strategy
        print(f"\n🛡️ Testing zero-loss strategy...")
        zero_loss_results = await self.test_zero_loss_strategy()
        
        # Generate final report
        report = self.generate_report(analysis_results, zero_loss_results)
        
        await self.api.disconnect()
        
        return report
    
    async def test_market(self, market: str) -> Dict[str, Any]:
        """Test a specific market"""
        # Subscribe to market ticks
        ticks = []
        
        async def tick_handler(tick_data):
            ticks.append(tick_data)
            if len(ticks) >= 100:
                return
        
        await self.api.subscribe_ticks(market, tick_handler)
        
        # Wait for ticks
        await asyncio.sleep(10)
        
        # Analyze market
        price_history = [t["quote"] for t in ticks]
        digits = [int(str(t["quote"])[-1]) for t in ticks]
        
        # Add to multi-market analyzer
        for i, (price, digit) in enumerate(zip(price_history, digits)):
            self.multi_market_analyzer.add_tick(market, price, [digit])
        
        # Run analysis
        analysis = self.analysis_manager.get_comprehensive_analysis({
            "last_20_digits": digits[-20:],
            "price_history": price_history,
            "current_price": price_history[-1],
            "market": market
        })
        
        # Calculate market score
        market_score = self.multi_market_analyzer._calculate_market_score(
            market, analysis, price_history
        )
        
        return {
            "market": market,
            "ticks_collected": len(ticks),
            "analysis": analysis,
            "score": market_score,
            "best_prediction": analysis.get("best_prediction"),
            "signals": analysis.get("signals", [])
        }
    
    async def test_all_analysis_types(self) -> Dict[str, Any]:
        """Test all analysis types (over/under, even/odd, rise/fall, match/diff)"""
        results = {}
        
        # Generate test data
        test_data = self._generate_test_data()
        
        # Test each analysis type
        analyzers = {
            "over_under": "over_under",
            "even_odd": "even_odd",
            "rise_fall": "rise_fall",
            "match_diff": "match_diff"
        }
        
        for name, analyzer_key in analyzers.items():
            result = self.analysis_manager.analyzers[analyzer_key].analyze(test_data)
            results[name] = {
                "prediction": result.prediction,
                "confidence": result.confidence,
                "data": result.data
            }
        
        return results
    
    async def test_zero_loss_strategy(self) -> Dict[str, Any]:
        """Test zero-loss strategy"""
        # Generate historical data
        historical_data = self._generate_historical_data(1000)
        
        # Test with sniper strategy
        sniper = SniperStrategy(min_confidence=90)
        backtester = Backtester()
        backtester.add_strategy(sniper)
        
        sniper_results = backtester.run_backtest(historical_data, "sniper")
        
        # Test with HFT strategy
        hft = HFTStrategy(min_confidence=80)
        backtester2 = Backtester()
        backtester2.add_strategy(hft)
        
        hft_results = backtester2.run_backtest(historical_data, "hft")
        
        return {
            "sniper": sniper_results,
            "hft": hft_results,
            "best_strategy": "sniper" if sniper_results["roi"] > hft_results["roi"] else "hft"
        }
    
    def _generate_test_data(self) -> Dict[str, Any]:
        """Generate test data for analysis"""
        import random
        digits = [random.randint(0, 9) for _ in range(20)]
        prices = [10000 + random.random() * 100 for _ in range(50)]
        
        return {
            "last_20_digits": digits,
            "price_history": prices,
            "current_price": prices[-1]
        }
    
    def _generate_historical_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate historical data for backtesting"""
        import random
        data = []
        price = 10000.0
        
        for _ in range(count):
            price += random.uniform(-50, 50)
            digits = [int(str(price)[-1])]
            data.append({
                "price": price,
                "digits": digits,
                "timestamp": datetime.now().isoformat()
            })
        
        return data
    
    def generate_report(self, analysis_results: Dict, zero_loss_results: Dict) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        # Calculate overall performance
        market_scores = {k: v["score"] for k, v in self.test_results.items()}
        best_market = max(market_scores.items(), key=lambda x: x[1])
        
        # Calculate analysis accuracy
        analysis_accuracy = {}
        for name, result in analysis_results.items():
            analysis_accuracy[name] = result["confidence"]
        
        # Calculate strategy performance
        sniper_roi = zero_loss_results["sniper"]["roi"]
        hft_roi = zero_loss_results["hft"]["roi"]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_markets_tested": len(self.test_results),
                "best_market": best_market[0],
                "best_market_score": best_market[1],
                "average_market_score": sum(market_scores.values()) / len(market_scores),
                "best_strategy": zero_loss_results["best_strategy"],
                "best_strategy_roi": max(sniper_roi, hft_roi)
            },
            "market_results": self.test_results,
            "analysis_results": analysis_results,
            "strategy_results": zero_loss_results,
            "analysis_accuracy": analysis_accuracy,
            "recommendations": self._generate_recommendations(market_scores, analysis_accuracy)
        }
    
    def _generate_recommendations(self, market_scores: Dict, analysis_accuracy: Dict) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Market recommendations
        best_market = max(market_scores.items(), key=lambda x: x[1])
        recommendations.append(f"Trade primarily on {best_market[0]} for best results")
        
        # Analysis recommendations
        best_analysis = max(analysis_accuracy.items(), key=lambda x: x[1])
        recommendations.append(f"Focus on {best_analysis[0]} analysis for highest accuracy")
        
        # Strategy recommendations
        recommendations.append("Use Sniper strategy for high-precision trades")
        recommendations.append("Use HFT strategy for quick opportunities")
        
        return recommendations


async def main():
    """Main test runner"""
    import os
    
    api_token = os.getenv("DERIV_API_TOKEN")
    if not api_token:
        print("❌ DERIV_API_TOKEN not set")
        return
    
    tester = DerivFullTest(api_token)
    report = await tester.run_full_test()
    
    print("\n" + "="*50)
    print("📊 TEST REPORT")
    print("="*50)
    print(json.dumps(report, indent=2))
    
    # Save report
    with open("deriv_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\n✅ Test report saved to deriv_test_report.json")


if __name__ == "__main__":
    asyncio.run(main())
