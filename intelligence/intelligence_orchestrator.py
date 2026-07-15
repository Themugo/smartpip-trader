"""
Intelligence Orchestrator — ties all 10 intelligence components into a single
decision pipeline.

Default policy: NO TRADE unless evidence exceeds configurable thresholds.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple

from .regime_detector import RegimeDetector
from .opportunity_scorer import OpportunityScorer
from .trade_memory import TradeMemory, TradeRecord
from .case_based_reasoner import CaseBasedReasoner
from .rl_agent import RLAgent
from .retraining_pipeline import RetrainingPipeline
from .explainable_ai import ExplainableAI
from .dynamic_sizer import DynamicSizer
from .meta_ai import MetaAI
from .digital_twin import DigitalTwin

logger = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """
    Central coordinator for the AI-first intelligence layer.

    Decision pipeline (every tick when auto-trading is on):
      1. Detect market regime
      2. Score opportunity (composite 0-100)
      3. Retrieve similar historical cases
      4. Get RL agent recommendation
      5. Run Digital Twin simulation
      6. If all gates pass → calculate position size
      7. Generate explanation for the decision
      8. Record everything for continual learning
    """

    def __init__(
        self,
        analysis_manager=None,
        settings=None,
        data_dir: str = "intelligence_data",
    ):
        self.settings = settings
        self._data_dir = data_dir

        # --- Core components ---
        self.trade_memory = TradeMemory(db_path=f"{data_dir}/trades_memory.db")
        self.regime_detector = RegimeDetector()
        self.opportunity_scorer = OpportunityScorer()
        self.case_reasoner = CaseBasedReasoner(trade_memory=self.trade_memory)
        self.rl_agent = RLAgent()
        self.meta_ai = MetaAI(
            analysis_manager=analysis_manager,
            trade_memory=self.trade_memory,
        )
        self.dynamic_sizer = DynamicSizer(
            trade_memory=self.trade_memory, settings=settings
        )
        self.digital_twin = DigitalTwin(trade_memory=self.trade_memory)
        self.explainable_ai = ExplainableAI(
            db_path=f"{data_dir}/explanations.db"
        )
        self.retraining_pipeline = RetrainingPipeline(
            trade_memory=self.trade_memory,
            ensemble_predictor=None,
            regime_detector=self.regime_detector,
            opportunity_scorer=self.opportunity_scorer,
            meta_ai=self.meta_ai,
        )

        # --- State ---
        self.current_regime = None
        self.current_opportunity = None
        self.last_explanation = None
        self._tick_count = 0
        self._trade_count = 0
        self._abstain_count = 0
        self._reject_count = 0

        logger.info("IntelligenceOrchestrator initialised")

    # ------------------------------------------------------------------
    # Public: per-tick intelligence pipeline
    # ------------------------------------------------------------------

    def evaluate_tick(
        self,
        price_history: list,
        digit_history: list,
        analyzer_output: dict,
        market: str,
        hour: int,
    ) -> Dict[str, Any]:
        """
        Run the full intelligence pipeline on every tick.

        Returns a decision dict:
          { decision: "TRADE"|"ABSTAIN"|"REJECT",
            score: float,
            size: float|None,
            explanation: TradeExplanation,
            regime: MarketRegime,
            opportunity: OpportunityScore,
            twin_result: TwinResult|None,
            rl_action: RLAction,
            similar_cases: list }
        """
        self._tick_count += 1
        t0 = time.time()

        # 1. Regime detection
        regime = self.regime_detector.detect(
            price_history=list(price_history),
            digit_history=list(digit_history),
        )
        self.current_regime = regime

        # 2. Opportunity scoring
        entropy = self._extract_entropy(analyzer_output)
        volatility = self._extract_volatility(price_history)
        historical_sim = self._get_historical_similarity(market, regime.regime)
        model_accuracy = self._get_model_accuracy()

        opportunity = self.opportunity_scorer.score(
            analyzer_output=analyzer_output,
            entropy=entropy,
            volatility=volatility,
            historical_similarity=historical_sim,
            model_accuracy=model_accuracy,
            regime=regime.regime,
            digit_history=digit_history,
            hour=hour,
        )
        self.current_opportunity = opportunity

        # 3. Case-based reasoning
        current_features = self._build_features(
            analyzer_output, entropy, volatility, regime
        )
        similar_cases = self.case_reasoner.retrieve(
            current_features=current_features,
            market=market,
            regime=regime.regime,
            n=5,
        )
        case_eval = self.case_reasoner.evaluate(current_features=current_features)

        # 4. RL agent
        rl_state = self._build_rl_state(
            regime.regime, entropy, volatility, analyzer_output, hour
        )
        rl_action = self.rl_agent.get_action(state=rl_state)

        # 5. Decision gate — default is NO TRADE
        decision = "ABSTAIN"
        rejection_reason = ""

        if opportunity.score < self.settings.min_opportunity_score if hasattr(self.settings, 'min_opportunity_score') else 75:
            decision = "ABSTAIN"
            rejection_reason = (
                f"Opportunity score {opportunity.score:.1f} below threshold"
            )
        elif rl_action.action == "ABSTAIN":
            decision = "ABSTAIN"
            rejection_reason = "RL agent recommends abstention"
        elif regime.regime == "RANDOM" and (self.settings.min_opportunity_score if hasattr(self.settings, 'min_opportunity_score') else 75) > 70:
            decision = "ABSTAIN"
            rejection_reason = "Random regime with high threshold"
        else:
            # 6. Digital Twin simulation
            twin_result = self.digital_twin.simulate(
                signal={
                    "direction": analyzer_output.get("consensus", {}).get("direction", "CALL"),
                    "confidence": analyzer_output.get("consensus", {}).get("confidence", 0),
                    "type": analyzer_output.get("consensus", {}).get("type", "UNKNOWN"),
                },
                market=market,
                regime=regime.regime,
                amount=self.settings.base_amount,
                n_simulations=500,
            )

            if not twin_result.approved:
                decision = "REJECT"
                rejection_reason = (
                    f"Digital Twin rejected: win rate {twin_result.simulated_win_rate:.1%} "
                    f"< {self.digital_twin.min_twin_threshold:.0%} threshold"
                )
            else:
                decision = "TRADE"

        # 7. Position sizing (only if TRADE)
        size_info = None
        if decision == "TRADE":
            historical_edge = case_eval.get("avg_profit_in_similar", 0)
            size_info = self.dynamic_sizer.calculate_size(
                confidence=opportunity.score,
                regime=regime.regime,
                entropy=entropy,
                historical_edge=historical_edge,
                kelly_fraction=getattr(self.settings, "kelly_fraction", 0.25),
                base_amount=getattr(self.settings, "base_amount", 1.0),
            )

        # 8. Explanation
        risk_check = {"can_trade": decision == "TRADE", "reason": rejection_reason}
        twin_dict = None
        if decision in ("TRADE", "REJECT"):
            twin_result_obj = self.digital_twin.simulate(
                signal={
                    "direction": analyzer_output.get("consensus", {}).get("direction", "CALL"),
                    "confidence": analyzer_output.get("consensus", {}).get("confidence", 0),
                    "type": analyzer_output.get("consensus", {}).get("type", "UNKNOWN"),
                },
                market=market,
                regime=regime.regime,
                amount=self.settings.base_amount,
                n_simulations=300,
            )
            twin_dict = {
                "approved": twin_result_obj.approved,
                "simulated_win_rate": twin_result_obj.simulated_win_rate,
            }

        explanation = self.explainable_ai.explain_trade_decision(
            analyzer_output=analyzer_output,
            opportunity_score=opportunity,
            regime=regime,
            trade_memory_stats=self.trade_memory.get_stats(),
            case_reasoner_output=case_eval,
            rl_action=rl_action,
            digital_twin_result=twin_dict,
            risk_check=risk_check,
        )
        self.last_explanation = explanation

        # 9. Counters
        if decision == "TRADE":
            self._trade_count += 1
        elif decision == "ABSTAIN":
            self._abstain_count += 1
        else:
            self._reject_count += 1

        elapsed = time.time() - t0
        logger.info(
            "Intelligence pipeline: decision=%s score=%.1f regime=%s twin=%.1f%% rl=%s (%.3fs)",
            decision,
            opportunity.score,
            regime.regime,
            (twin_dict or {}).get("simulated_win_rate", 0) * 100,
            rl_action.action,
            elapsed,
        )

        return {
            "decision": decision,
            "rejection_reason": rejection_reason,
            "score": opportunity.score,
            "size": size_info.get("amount") if size_info else None,
            "size_info": size_info,
            "explanation": explanation,
            "regime": regime,
            "opportunity": opportunity,
            "twin_result": twin_dict,
            "rl_action": rl_action,
            "similar_cases": similar_cases,
            "case_eval": case_eval,
        }

    # ------------------------------------------------------------------
    # Post-trade: record outcome for continual learning
    # ------------------------------------------------------------------

    def record_trade_outcome(
        self,
        trade_record: TradeRecord,
        analyzer_output: dict,
    ):
        """Feed a completed trade back into all learning components."""
        # Trade memory
        self.trade_memory.record_trade(trade_record)

        # Case-based reasoner
        self.case_reasoner.index_new_case(trade_record)

        # RL agent: compute reward
        reward = self.rl_agent.compute_reward(
            profit=trade_record.profit,
            was_trade=True,
        )
        # Update RL with the state from when trade was taken
        # (simplified: use current features as proxy)
        rl_state = {
            "regime": trade_record.market_features.get("regime", "UNKNOWN"),
            "entropy_level": self._discretise_entropy(
                trade_record.market_features.get("entropy", 3.0)
            ),
            "volatility_level": self._discretise_volatility(
                trade_record.market_features.get("volatility", 0.0)
            ),
            "consensus_level": self._discretise_consensus(
                trade_record.confidence
            ),
            "time_bin": 12,
        }
        self.rl_agent.update(
            state=rl_state,
            action="TRADE",
            reward=reward,
            next_state=rl_state,
        )

        # Dynamic sizer
        self.dynamic_sizer.record_trade_outcome(trade_record.profit)

        # Digital twin calibration
        self.digital_twin.calibrate(
            actual_outcomes=[
                {
                    "predicted_direction": trade_record.direction,
                    "actual_profit": trade_record.profit,
                }
            ]
        )

        logger.info(
            "Trade outcome recorded: profit=%.4f outcome=%s",
            trade_record.profit,
            trade_record.outcome,
        )

    # ------------------------------------------------------------------
    # Meta operations
    # ------------------------------------------------------------------

    def run_nightly_retrain(self) -> dict:
        """Trigger the nightly retraining pipeline."""
        return self.retraining_pipeline.run_nightly_retrain()

    def get_intelligence_state(self) -> Dict[str, Any]:
        """Full intelligence state for API/dashboard."""
        return {
            "regime": {
                "current": self.current_regime.regime if self.current_regime else None,
                "confidence": self.current_regime.confidence if self.current_regime else None,
                "stats": self.regime_detector.get_regime_stats(),
            },
            "opportunity": {
                "score": self.current_opportunity.score if self.current_opportunity else None,
                "recommendation": self.current_opportunity.recommendation if self.current_opportunity else None,
                "components": self.current_opportunity.components if self.current_opportunity else {},
                "stats": self.opportunity_scorer.get_scoring_stats(),
            },
            "trade_memory": self.trade_memory.get_stats(),
            "case_reasoner": self.case_reasoner.get_case_stats(),
            "rl_agent": self.rl_agent.get_q_table_stats(),
            "meta_ai": self.meta_ai.get_analyzer_report(),
            "dynamic_sizer": self.dynamic_sizer.get_sizing_stats(),
            "digital_twin": self.digital_twin.get_twin_stats(),
            "explainable_ai": self.explainable_ai.get_decision_stats(),
            "pipeline_stats": {
                "ticks_evaluated": self._tick_count,
                "trades_recommended": self._trade_count,
                "abstentions": self._abstain_count,
                "rejections": self._reject_count,
            },
            "last_explanation": {
                "decision": self.last_explanation.decision,
                "score": self.last_explanation.score,
                "factors": [
                    {"name": f["name"], "contribution": f["contribution"]}
                    for f in self.last_explanation.factors
                ],
            }
            if self.last_explanation
            else None,
        }

    def save_all(self):
        """Persist all component states to disk."""
        self.regime_detector.save(f"{self._data_dir}/regime_detector.pkl")
        self.rl_agent.save(f"{self._data_dir}/rl_agent.pkl")
        self.meta_ai.save(f"{self._data_dir}/meta_ai.pkl")
        self.digital_twin.save(f"{self._data_dir}/digital_twin.pkl")
        logger.info("All intelligence components saved to %s", self._data_dir)

    def load_all(self):
        """Load all component states from disk."""
        self.regime_detector.load(f"{self._data_dir}/regime_detector.pkl")
        self.rl_agent.load(f"{self._data_dir}/rl_agent.pkl")
        self.meta_ai.load(f"{self._data_dir}/meta_ai.pkl")
        self.digital_twin.load(f"{self._data_dir}/digital_twin.pkl")
        logger.info("All intelligence components loaded from %s", self._data_dir)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_entropy(analyzer_output: dict) -> float:
        for key in ("entropy", "market_entropy"):
            if key in analyzer_output:
                return float(analyzer_output[key])
        pr = analyzer_output.get("pattern_recognizer", {})
        if isinstance(pr, dict):
            data = pr.get("data", {})
            return float(data.get("entropy", 3.0))
        return 3.0

    @staticmethod
    def _extract_volatility(price_history) -> float:
        if len(price_history) < 10:
            return 0.0
        import numpy as np
        prices = list(price_history)[-50:]
        returns = np.diff(prices) / np.array(prices[:-1]) if len(prices) > 1 else [0]
        return float(np.std(returns)) if len(returns) > 0 else 0.0

    def _get_historical_similarity(self, market: str, regime: str) -> float:
        stats = self.trade_memory.get_stats()
        if stats.get("total_trades", 0) < 10:
            return 0.5
        market_stats = stats.get("by_market", {}).get(market, {})
        win_rate = market_stats.get("win_rate", 0.5)
        return win_rate

    def _get_model_accuracy(self) -> float:
        try:
            report = self.meta_ai.get_analyzer_report()
            avg = report.get("average_win_rate", 0.5)
            return avg
        except Exception:
            return 0.5

    @staticmethod
    def _build_features(analyzer_output, entropy, volatility, regime) -> dict:
        consensus = analyzer_output.get("consensus", {})
        return {
            "entropy": entropy,
            "volatility": volatility,
            "regime": regime.regime,
            "regime_confidence": regime.confidence,
            "consensus_confidence": consensus.get("confidence", 0),
            "consensus_direction": consensus.get("direction", "UNKNOWN"),
            "n_agreeing": consensus.get("n_agreeing", 0),
            "n_total": consensus.get("n_total", 0),
        }

    @staticmethod
    def _build_rl_state(regime, entropy, volatility, analyzer_output, hour) -> dict:
        def _disc(val, thresholds):
            for i, t in enumerate(thresholds):
                if val < t:
                    return i
            return len(thresholds)

        consensus = analyzer_output.get("consensus", {})
        return {
            "regime": regime,
            "entropy_level": _disc(entropy, [1.5, 2.2, 2.8]),
            "volatility_level": _disc(volatility, [0.001, 0.005, 0.01]),
            "consensus_level": _disc(consensus.get("confidence", 0), [40, 60, 80]),
            "time_bin": hour // 6,
        }

    @staticmethod
    def _discretise_entropy(val: float) -> int:
        if val < 1.5:
            return 0
        if val < 2.2:
            return 1
        if val < 2.8:
            return 2
        return 3

    @staticmethod
    def _discretise_volatility(val: float) -> int:
        if val < 0.001:
            return 0
        if val < 0.005:
            return 1
        if val < 0.01:
            return 2
        return 3

    @staticmethod
    def _discretise_consensus(val: float) -> int:
        if val < 40:
            return 0
        if val < 60:
            return 1
        if val < 80:
            return 2
        return 3
