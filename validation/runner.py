"""
Validation runner: executes full quantitative audit across all strategies and markets.
Generates comprehensive report and deployment recommendation.
"""
import json
import sys
from typing import Dict, Any, List
from datetime import datetime
from .market_simulator import MultiMarketSimulator, MarketSimulator, SimulationConfig
from .strategy_tester import (
    StrategyTester, EvenOddStrategy, OverUnderStrategy, MatchDiffStrategy,
    CompositeStrategy, PerformanceMetrics
)


class ValidationRunner:
    """Runs complete strategy validation suite"""
    
    def __init__(self, num_ticks: int = 15000, num_mc_sims: int = 1000):
        self.num_ticks = num_ticks
        self.num_mc_sims = num_mc_sims
        self.results: Dict[str, Any] = {}
    
    def run_all(self) -> Dict[str, Any]:
        """Run validation on all strategies across all markets"""
        print("=" * 70)
        print("SMARTPIP STRATEGY VALIDATION AUDIT")
        print("=" * 70)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Simulated ticks per market: {self.num_ticks}")
        print(f"Monte Carlo simulations: {self.num_mc_sims}")
        print()
        
        # Create market simulators
        simulators = MultiMarketSimulator.create_simulators(self.num_ticks)
        
        # Generate ticks for all markets
        market_ticks = {}
        for symbol, sim in simulators.items():
            print(f"Generating {self.num_ticks} ticks for {symbol}...")
            market_ticks[symbol] = sim.generate_ticks()
        
        # Define strategies
        strategies = [
            ("EvenOdd_MeanReversion", EvenOddStrategy(min_confidence=55)),
            ("EvenOdd_Aggressive", EvenOddStrategy(min_confidence=50)),
            ("OverUnder_Barrier5", OverUnderStrategy(barrier=5, min_confidence=55)),
            ("OverUnder_Barrier4", OverUnderStrategy(barrier=4, min_confidence=55)),
            ("MatchDiff_Streak", MatchDiffStrategy(min_confidence=55)),
            ("MatchDiff_Conservative", MatchDiffStrategy(min_confidence=60)),
            ("Composite_All", CompositeStrategy([
                EvenOddStrategy(min_confidence=55),
                OverUnderStrategy(barrier=5, min_confidence=55),
                MatchDiffStrategy(min_confidence=55),
            ], min_agreement=2)),
        ]
        
        all_results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "num_ticks": self.num_ticks,
                "num_mc_sims": self.num_mc_sims,
                "markets": list(market_ticks.keys()),
                "strategies": [name for name, _ in strategies],
            },
            "results": {},
            "summary": {},
            "deployable": {},
        }
        
        # Run each strategy on each market
        for strategy_name, strategy in strategies:
            print(f"\n{'='*70}")
            print(f"Strategy: {strategy_name}")
            print(f"{'='*70}")
            
            strategy_results = {}
            
            for symbol, ticks in market_ticks.items():
                print(f"  Testing on {symbol}...", end=" ")
                
                tester = StrategyTester(
                    strategy=strategy,
                    amount=1.0,
                    payout_rate=0.94,
                    fee_per_trade=0.0,
                    slippage_std=0.0005,
                    latency_ticks=1,
                )
                
                result = tester.full_validation(ticks, num_mc_sims=self.num_mc_sims)
                strategy_results[symbol] = result
                
                oos = result.get("out_of_sample", {})
                deployable = result.get("deployable", False)
                status = "PASS" if deployable else "FAIL"
                
                print(f"Trades: {oos.get('total_trades', 0)} | "
                      f"Expectancy: {oos.get('expectancy', 0):.4f} | "
                      f"Win Rate: {oos.get('win_rate', 0):.1f}% | "
                      f"Sharpe: {oos.get('sharpe_ratio', 0):.3f} | "
                      f"Max DD: ${oos.get('max_drawdown', 0):.2f} | "
                      f"[{status}]")
            
            all_results["results"][strategy_name] = strategy_results
            
            # Strategy summary
            total_trades = sum(r["out_of_sample"].get("total_trades", 0) 
                             for r in strategy_results.values())
            avg_expectancy = sum(r["out_of_sample"].get("expectancy", 0) 
                                for r in strategy_results.values()) / len(strategy_results)
            avg_win_rate = sum(r["out_of_sample"].get("win_rate", 0) 
                              for r in strategy_results.values()) / len(strategy_results)
            deployable_count = sum(1 for r in strategy_results.values() if r.get("deployable", False))
            
            all_results["summary"][strategy_name] = {
                "total_trades": total_trades,
                "avg_expectancy": round(avg_expectancy, 4),
                "avg_win_rate": round(avg_win_rate, 2),
                "markets_deployable": deployable_count,
                "total_markets": len(strategy_results),
                "overall_deployable": deployable_count == len(strategy_results),
            }
            
            all_results["deployable"][strategy_name] = deployable_count == len(strategy_results)
        
        self.results = all_results
        return all_results
    
    def generate_report(self) -> str:
        """Generate human-readable validation report"""
        if not self.results:
            return "No results. Run validation first."
        
        lines = []
        lines.append("=" * 80)
        lines.append("SMARTPIP STRATEGY VALIDATION REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {self.results['metadata']['timestamp']}")
        lines.append(f"Markets: {', '.join(self.results['metadata']['markets'])}")
        lines.append(f"Strategies: {len(self.results['metadata']['strategies'])}")
        lines.append(f"Ticks per market: {self.results['metadata']['num_ticks']:,}")
        lines.append(f"Monte Carlo sims: {self.results['metadata']['num_mc_sims']:,}")
        lines.append("")
        
        # Overall deployment status
        lines.append("-" * 80)
        lines.append("DEPLOYMENT GATE")
        lines.append("-" * 80)
        
        any_deployable = False
        for strategy_name, deployable in self.results["deployable"].items():
            status = "DEPLOYABLE" if deployable else "BLOCKED"
            color_symbol = "OK" if deployable else "XX"
            lines.append(f"  [{color_symbol}] {strategy_name}: {status}")
            if deployable:
                any_deployable = True
        
        if not any_deployable:
            lines.append("\n  WARNING: NO STRATEGIES PASSED VALIDATION. DEPLOYMENT BLOCKED.")
        lines.append("")
        
        # Per-strategy details
        for strategy_name in self.results["metadata"]["strategies"]:
            lines.append("-" * 80)
            lines.append(f"STRATEGY: {strategy_name}")
            lines.append("-" * 80)
            
            summary = self.results["summary"][strategy_name]
            lines.append(f"  Total Trades (all markets): {summary['total_trades']:,}")
            lines.append(f"  Avg Expectancy: {summary['avg_expectancy']:.4f}")
            lines.append(f"  Avg Win Rate: {summary['avg_win_rate']:.2f}%")
            lines.append(f"  Markets Deployable: {summary['markets_deployable']}/{summary['total_markets']}")
            lines.append("")
            
            for symbol, result in self.results["results"][strategy_name].items():
                lines.append(f"  --- {symbol} ---")
                oos = result.get("out_of_sample", {})
                mc = result.get("monte_carlo", {})
                
                lines.append(f"    OOS Trades: {oos.get('total_trades', 0)}")
                lines.append(f"    Win Rate: {oos.get('win_rate', 0):.2f}%")
                lines.append(f"    Profit Factor: {oos.get('profit_factor', 0):.3f}")
                lines.append(f"    Expectancy: ${oos.get('expectancy', 0):.4f}")
                lines.append(f"    Sharpe Ratio: {oos.get('sharpe_ratio', 0):.3f}")
                lines.append(f"    Max Drawdown: ${oos.get('max_drawdown', 0):.2f}")
                lines.append(f"    Recovery Factor: {oos.get('recovery_factor', 0):.3f}")
                lines.append(f"    MC Prob Profit: {mc.get('prob_profit', 0)*100:.1f}%")
                lines.append(f"    MC 95% CI: [{mc.get('confidence_95', (0,0))[0]:.2f}, {mc.get('confidence_95', (0,0))[1]:.2f}]")
                lines.append(f"    Deployable: {'YES' if result.get('deployable', False) else 'NO'}")
                
                if oos.get("validation_errors"):
                    for err in oos["validation_errors"]:
                        lines.append(f"    ERROR: {err}")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_results(self, filepath: str = "validation_results.json") -> None:
        """Save results to JSON"""
        with open(filepath, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\nResults saved to {filepath}")
    
    def save_report(self, filepath: str = "VALIDATION_REPORT.md") -> None:
        """Save report to markdown file"""
        report = self.generate_report()
        with open(filepath, "w") as f:
            f.write(report)
        print(f"Report saved to {filepath}")


def main():
    """Main entry point for validation"""
    runner = ValidationRunner(num_ticks=15000, num_mc_sims=1000)
    runner.run_all()
    runner.save_results()
    runner.save_report()
    
    # Print report to console
    print("\n" + runner.generate_report())
    
    # Exit code based on deployability
    any_deployable = any(runner.results["deployable"].values())
    sys.exit(0 if any_deployable else 1)


if __name__ == "__main__":
    main()
