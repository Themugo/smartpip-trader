"""
Research Orchestrator — ties all 12 advanced intelligence modules into a
single unified decision pipeline, replacing the original IntelligenceOrchestrator
as the central coordinator for the world-class upgrade.

Pipeline steps (evaluate_tick):
  1.  MarketDNA.compute_fingerprint  — deep market fingerprinting
  2.  MarketDNA.detect_anomaly       — anomaly detection
  3.  SimilaritySearch.search        — historical pattern matching
  4.  EnsembleIntelligence.aggregate — multi-model ensemble aggregation
  5.  BayesianEngine.evaluate_signal — uncertainty quantification
  6.  OnlineLearner.predict_with_uncertainty — online learning prediction
  7.  MetaSupervisor.supervise       — meta-learning calibration
  8.  AbstentionModel.evaluate       — intelligent abstention
  9.  CapitalPreservation.should_allow_trade + evaluate_risk — risk gate
  10. CapitalPreservation.calculate_position_size — position sizing
  11. ExplainableEngine.explain      — structured explanation
  12. Record everything for learning

Default policy: NO TRADE unless evidence exceeds configurable thresholds.
Graceful fallback to the original IntelligenceOrchestrator on any failure.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import joblib

from .market_dna import MarketDNA, DNAFingerprint, AnomalyReport
from .similarity_search import SimilaritySearch, SearchResult
from .bayesian_engine import BayesianEngine, BayesianVerdict
from .ensemble_intelligence import EnsembleIntelligence, ModelVote, EnsembleVerdict
from .online_learner import OnlineLearner, DriftReport, LearningState
from .abstention_model import AbstentionModel, AbstentionVerdict
from .meta_supervisor import MetaSupervisor, CalibrationReport, MetaReport
from .explainable_engine import ExplainableEngine, StructuredExplanation
from .backtesting_engine import BacktestingEngine, BacktestResult
from .capital_preservation import CapitalPreservation, RiskState
from .self_improvement import SelfImprovementPipeline, ImprovementAttempt
from .intelligence_orchestrator import IntelligenceOrchestrator

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    """
    Central research-grade orchestrator coordinating all 12 advanced
    intelligence modules into a single decision pipeline.

    Falls back to the original IntelligenceOrchestrator on any failure,
    ensuring uninterrupted trading even if the research layer errors out.
    """

    def __init__(
        self,
        analysis_manager=None,
        settings=None,
        data_dir: str = "intelligence_data",
    ):
        self.settings = settings
        self._data_dir = data_dir

        # --- Legacy fallback ---
        self._legacy = IntelligenceOrchestrator(
            analysis_manager=analysis_manager,
            settings=settings,
            data_dir=data_dir,
        )

        # --- Advanced module 1: MarketDNA ---
        self.market_dna = MarketDNA(n_clusters=6)

        # --- Advanced module 2: SimilaritySearch ---
        self.similarity_search = SimilaritySearch()

        # --- Advanced module 3: BayesianEngine ---
        self.bayesian_engine = BayesianEngine()

        # --- Advanced module 4: EnsembleIntelligence ---
        self.ensemble_intelligence = EnsembleIntelligence()

        # --- Advanced module 5: OnlineLearner ---
        self.online_learner = OnlineLearner()

        # --- Advanced module 6: AbstentionModel ---
        self.abstention_model = AbstentionModel()

        # --- Advanced module 7: MetaSupervisor ---
        self.meta_supervisor = MetaSupervisor()

        # --- Advanced module 8: ExplainableEngine ---
        self.explainable_engine = ExplainableEngine(
            db_path=f"{data_dir}/explanation_engine.db",
        )

        # --- Advanced module 9: BacktestingEngine ---
        self.backtesting_engine = BacktestingEngine()

        # --- Advanced module 10: CapitalPreservation ---
        self.capital_preservation = CapitalPreservation()

        # --- Advanced module 11: SelfImprovementPipeline ---
        self.self_improvement = SelfImprovementPipeline(
            component_paths={
                "market_dna": f"{data_dir}/market_dna.pkl",
                "bayesian_engine": f"{data_dir}/bayesian_engine.pkl",
                "ensemble_intelligence": f"{data_dir}/ensemble_intelligence.pkl",
                "online_learner": f"{data_dir}/online_learner.pkl",
                "abstention_model": f"{data_dir}/abstention_model.pkl",
                "meta_supervisor": f"{data_dir}/meta_supervisor.pkl",
                "capital_preservation": f"{data_dir}/capital_preservation.pkl",
            },
            retrain_fn=self._retrain_callback,
            metrics_fn=self._metrics_callback,
        )

        # --- State ---
        self._tick_count = 0
        self._trade_count = 0
        self._abstain_count = 0
        self._reject_count = 0
        self._last_fingerprint: Optional[DNAFingerprint] = None
        self._last_anomaly: Optional[AnomalyReport] = None
        self._last_search_results: List[SearchResult] = []
        self._last_ensemble_verdict: Optional[EnsembleVerdict] = None
        self._last_bayesian_verdict: Optional[BayesianVerdict] = None
        self._last_learning_state: Optional[LearningState] = None
        self._last_abstention_verdict: Optional[AbstentionVerdict] = None
        self._last_risk_state: Optional[RiskState] = None
        self._last_explanation: Optional[StructuredExplanation] = None
        self._last_meta_reports: Optional[Dict[str, CalibrationReport]] = None
        self._consecutive_losses: int = 0
        self._features_buffer: List[Dict[str, float]] = []

        logger.info("ResearchOrchestrator initialised with 12 advanced modules")

    # ------------------------------------------------------------------
    # Main pipeline
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
        Run the full 12-step research pipeline on every tick.

        Returns a decision dict with keys covering every stage.
        Falls back to the legacy IntelligenceOrchestrator if anything fails.
        """
        self._tick_count += 1
        t0 = time.time()

        try:
            return self._run_pipeline(
                price_history, digit_history, analyzer_output, market, hour,
            )
        except Exception as exc:
            logger.exception(
                "Research pipeline failed at tick %d: %s — falling back to legacy",
                self._tick_count, exc,
            )
            return self._legacy.evaluate_tick(
                price_history, digit_history, analyzer_output, market, hour,
            )

    def _run_pipeline(
        self,
        price_history: list,
        digit_history: list,
        analyzer_output: dict,
        market: str,
        hour: int,
    ) -> Dict[str, Any]:
        """Internal 12-step pipeline implementation."""
        t0 = time.time()
        decision = "ABSTAIN"
        rejection_reason = ""
        size_info = None

        # ----------------------------------------------------------------
        # Step 1: Market DNA fingerprinting
        # ----------------------------------------------------------------
        fingerprint = self.market_dna.compute_fingerprint(
            market=market,
            price_history=list(price_history),
            digit_history=list(digit_history),
        )
        self._last_fingerprint = fingerprint

        # ----------------------------------------------------------------
        # Step 2: Anomaly detection
        # ----------------------------------------------------------------
        anomaly = self.market_dna.detect_anomaly(market, fingerprint)
        self._last_anomaly = anomaly

        # ----------------------------------------------------------------
        # Step 3: Similarity search
        # ----------------------------------------------------------------
        regime_str = self._extract_regime_str(analyzer_output)
        entropy_val = self._extract_entropy(analyzer_output)
        consensus_conf = analyzer_output.get("consensus", {}).get("confidence", 50.0)
        consensus_dir = analyzer_output.get("consensus", {}).get("direction", "CALL")

        query_features = SimilaritySearch._extract_features(
            price_history=list(price_history),
            digit_history=list(digit_history),
            regime=regime_str,
            hour=hour,
            confidence=consensus_conf,
            direction=consensus_dir,
        )
        search_results = self.similarity_search.search(
            query_features=query_features,
            top_k=10,
            regime_filter=regime_str if regime_str != "UNKNOWN" else None,
            market_filter=market,
        )
        self._last_search_results = search_results

        # ----------------------------------------------------------------
        # Step 4: Ensemble aggregation
        # ----------------------------------------------------------------
        votes = self._analyzer_output_to_votes(analyzer_output)
        ensemble_verdict = self.ensemble_intelligence.aggregate(
            votes=votes,
            regime=regime_str,
            min_agreement=0.5,
        )
        self._last_ensemble_verdict = ensemble_verdict

        # ----------------------------------------------------------------
        # Step 5: Bayesian confidence
        # ----------------------------------------------------------------
        analyzer_confidences = self._extract_analyzer_confidences(analyzer_output)
        bayesian_verdict = self.bayesian_engine.evaluate_signal(
            analyzer_confidences=analyzer_confidences,
            regime=regime_str,
            market=market,
        )
        self._last_bayesian_verdict = bayesian_verdict

        # ----------------------------------------------------------------
        # Step 6: Online learning prediction
        # ----------------------------------------------------------------
        features_for_learning = self._build_learning_features(
            fingerprint, ensemble_verdict, bayesian_verdict,
            price_history, digit_history,
        )
        base_pred = bayesian_verdict.overall_confidence
        online_prediction, online_uncertainty = self.online_learner.predict_with_uncertainty(
            features=features_for_learning,
            base_prediction=base_pred,
        )

        learning_state = LearningState(
            learning_rate=self.online_learner._learning_rate,
            total_updates=self.online_learner._total_updates,
            drift_events=self.online_learner._drift_events,
            current_ewma=self.online_learner._ewma.get_state() if hasattr(self.online_learner, '_ewma') else {},
            performance_trend=0.5,
            adaptation_count=self.online_learner._adaptation_count,
        )
        self._last_learning_state = learning_state

        # ----------------------------------------------------------------
        # Step 7: Meta supervision
        # ----------------------------------------------------------------
        meta_state = self._build_meta_state(analyzer_output)
        meta_reports = self.meta_supervisor.supervise(meta_state)
        self._last_meta_reports = meta_reports

        # ----------------------------------------------------------------
        # Step 8: Abstention check
        # ----------------------------------------------------------------
        volatility_val = self._extract_volatility(price_history)
        regime_conf = self._extract_regime_confidence(analyzer_output)
        agreement_val = ensemble_verdict.agreement_ratio
        opportunity_score_val = self._compute_opportunity_score(
            bayesian_verdict, ensemble_verdict, online_prediction,
        )
        drawdown_val = self._get_drawdown()
        consec_losses = self._consecutive_losses

        abstention_verdict = self.abstention_model.evaluate(
            volatility=volatility_val,
            regime_confidence=regime_conf,
            model_agreement=agreement_val,
            opportunity_score=opportunity_score_val,
            recent_drawdown=drawdown_val,
            hour=hour,
            entropy=entropy_val,
            consecutive_losses=consec_losses,
            daily_trades=self._trade_count,
        )
        self._last_abstention_verdict = abstention_verdict

        # ----------------------------------------------------------------
        # Step 9: Capital preservation gate
        # ----------------------------------------------------------------
        risk_state = self.capital_preservation.evaluate_risk(
            current_exposure_pct=0.0,
        )
        self._last_risk_state = risk_state

        trade_gate = self.capital_preservation.should_allow_trade(
            confidence=opportunity_score_val,
            current_exposure_pct=0.0,
        )

        # ----------------------------------------------------------------
        # Decision logic
        # ----------------------------------------------------------------
        if anomaly.is_anomaly:
            decision = "ABSTAIN"
            rejection_reason = (
                f"Market anomaly detected: {', '.join(anomaly.contributing_features)}"
            )
        elif abstention_verdict.should_abstain:
            decision = "ABSTAIN"
            rejection_reason = abstention_verdict.recommendation
        elif not trade_gate.allowed:
            decision = "REJECT"
            rejection_reason = trade_gate.reason
        elif bayesian_verdict.recommendation in ("LOW_CONFIDENCE", "INSUFFICIENT_DATA"):
            decision = "ABSTAIN"
            rejection_reason = (
                f"Bayesian recommendation: {bayesian_verdict.recommendation} "
                f"(conf={bayesian_verdict.overall_confidence:.2f})"
            )
        elif ensemble_verdict.disagreement_detected:
            decision = "ABSTAIN"
            rejection_reason = "Ensemble disagreement detected — models are split"
        elif ensemble_verdict.confidence < 50.0:
            decision = "ABSTAIN"
            rejection_reason = f"Ensemble confidence too low: {ensemble_verdict.confidence:.1f}"
        elif risk_state.risk_level in ("HIGH", "CRITICAL"):
            decision = "REJECT"
            rejection_reason = f"Risk level {risk_state.risk_level} — capital preservation engaged"
        else:
            decision = "TRADE"

        # ----------------------------------------------------------------
        # Step 10: Position sizing
        # ----------------------------------------------------------------
        if decision == "TRADE":
            win_rate = self._estimate_win_rate(
                search_results, bayesian_verdict, online_prediction,
            )
            avg_win = self._estimate_avg_win(search_results)
            avg_loss = self._estimate_avg_loss(search_results)

            size_info = self.capital_preservation.calculate_position_size(
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                confidence=opportunity_score_val,
                regime=regime_str,
                current_exposure_pct=0.0,
            )

        # ----------------------------------------------------------------
        # Step 11: Structured explanation
        # ----------------------------------------------------------------
        risk_check = {
            "can_trade": decision == "TRADE",
            "reason": rejection_reason,
            "consecutive_losses": consec_losses,
            "daily_pnl": risk_state.daily_pnl * 0.01 * 10000.0,
        }

        explanation = self.explainable_engine.explain(
            analyzer_output=analyzer_output,
            opportunity_score=self._make_opportunity_score_obj(opportunity_score_val),
            regime=self._make_regime_obj(regime_str, regime_conf),
            trade_memory_stats=self._legacy.trade_memory.get_stats(),
            case_reasoner_output={"win_rate_in_similar": 0.5, "recommendation": "NEUTRAL"},
            rl_action=self._legacy.rl_agent.get_action(
                state={"regime": regime_str, "entropy_level": 1, "volatility_level": 1, "consensus_level": 1, "time_bin": hour // 6},
            ) if hasattr(self._legacy.rl_agent, 'get_action') else None,
            digital_twin_result=self._legacy.digital_twin.simulate(
                signal={"direction": consensus_dir, "confidence": consensus_conf, "type": "UNKNOWN"},
                market=market,
                regime=regime_str,
                amount=getattr(self.settings, "base_amount", 1.0),
                n_simulations=300,
            ) if hasattr(self._legacy.digital_twin, 'simulate') else None,
            risk_check=risk_check,
            bayesian_verdict=bayesian_verdict,
            abstention_verdict=abstention_verdict,
            ensemble_verdict=ensemble_verdict,
        )
        self._last_explanation = explanation

        # ----------------------------------------------------------------
        # Step 12: Record for learning
        # ----------------------------------------------------------------
        self._record_pipeline_state(
            decision, search_results, features_for_learning,
        )

        # Counters
        if decision == "TRADE":
            self._trade_count += 1
        elif decision == "ABSTAIN":
            self._abstain_count += 1
        else:
            self._reject_count += 1

        elapsed = time.time() - t0
        logger.info(
            "Research pipeline: decision=%s score=%.1f ensemble=%.1f%% bayes=%.2f "
            "abstain=%.2f risk=%s anomaly=%s (%.3fs)",
            decision,
            opportunity_score_val,
            ensemble_verdict.confidence,
            bayesian_verdict.overall_confidence,
            abstention_verdict.abstention_probability,
            risk_state.risk_level,
            anomaly.is_anomaly,
            elapsed,
        )

        return {
            "decision": decision,
            "rejection_reason": rejection_reason,
            "score": opportunity_score_val,
            "size": size_info.get("amount") if size_info else None,
            "size_info": size_info,
            "explanation": explanation,
            "regime": self._make_regime_obj(regime_str, regime_conf),
            "opportunity": self._make_opportunity_score_obj(opportunity_score_val),
            "twin_result": None,
            "rl_action": None,
            "similar_cases": search_results,
            "case_eval": {"win_rate_in_similar": 0.5, "avg_profit_in_similar": 0.0},
            "bayesian_verdict": bayesian_verdict,
            "abstention_verdict": abstention_verdict,
            "ensemble_verdict": ensemble_verdict,
            "risk_state": risk_state,
            "dna_fingerprint": fingerprint,
            "anomaly_report": anomaly,
            "search_results": search_results,
            "meta_report": meta_reports,
            "learning_state": learning_state,
        }

    # ------------------------------------------------------------------
    # Post-trade feedback
    # ------------------------------------------------------------------

    def record_trade_outcome(
        self,
        trade_record,
        analyzer_output: dict,
    ):
        """Feed a completed trade back into all learning components."""
        try:
            # Legacy components
            self._legacy.record_trade_outcome(trade_record, analyzer_output)

            # Outcome
            profit = float(getattr(trade_record, "profit", 0.0))
            outcome = getattr(trade_record, "outcome", "LOSS")
            was_win = outcome.upper() in ("WIN", "WON")

            # Bayesian engine
            analyzer_confidences = self._extract_analyzer_confidences(analyzer_output)
            regime_str = self._extract_regime_str(analyzer_output)
            market = getattr(trade_record, "market", "unknown")
            self.bayesian_engine.update(
                outcome=was_win,
                analyzer_confidences=analyzer_confidences,
                regime=regime_str,
                market=market,
            )

            # Online learner
            if self._last_fingerprint is not None:
                feat = {
                    "volatility": self._last_fingerprint.features.get("volatility", 0.0),
                    "hurst": self._last_fingerprint.features.get("hurst", 0.5),
                    "entropy": self._last_fingerprint.features.get("entropy", 0.0),
                    "score": 0.5,
                }
                confidence = analyzer_output.get("consensus", {}).get("confidence", 50.0)
                self.online_learner.update(
                    features=feat,
                    outcome=was_win,
                    confidence=confidence,
                )

            # Ensemble intelligence
            votes = self._analyzer_output_to_votes(analyzer_output)
            for v in votes:
                correct = (
                    (v.direction.upper() in ("CALL", "RISE", "EVEN", "OVER") and was_win)
                    or (v.direction.upper() in ("PUT", "FALL", "ODD", "UNDER") and not was_win)
                )
                self.ensemble_intelligence.update_performance(
                    model_name=v.model_name,
                    correct=correct,
                    confidence=v.confidence,
                    regime=regime_str,
                )

            # Similarity search — index this pattern
            if self._last_fingerprint is not None:
                idx_id = f"trade_{int(time.time())}_{self._trade_count}"
                self.similarity_search.index_pattern(
                    record_id=idx_id,
                    features=self._last_fingerprint.features,
                    outcome="WIN" if was_win else "LOSS",
                    profit=profit,
                    regime=regime_str,
                    market=market,
                )

            # Capital preservation
            self.capital_preservation.update_after_trade(pnl=profit)

            # Abstention model
            if self._last_abstention_verdict is not None:
                self.abstention_model.record_outcome(
                    abstained=self._last_abstention_verdict.should_abstain,
                    trade_outcome="WIN" if was_win else "LOSS",
                    profit=profit,
                )

            # Consecutive losses
            if was_win:
                self._consecutive_losses = 0
            else:
                self._consecutive_losses += 1

            # Meta supervisor — update weights
            self.meta_supervisor.update_weights()

            logger.info(
                "Research trade outcome: profit=%.4f outcome=%s",
                profit, outcome,
            )

        except Exception as exc:
            logger.error(
                "record_trade_outcome failed: %s — delegating to legacy", exc,
            )
            self._legacy.record_trade_outcome(trade_record, analyzer_output)

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def get_intelligence_state(self) -> Dict[str, Any]:
        """Full intelligence state for API/dashboard."""
        try:
            return {
                "research_orchestrator": {
                    "ticks_evaluated": self._tick_count,
                    "trades_recommended": self._trade_count,
                    "abstentions": self._abstain_count,
                    "rejections": self._reject_count,
                    "consecutive_losses": self._consecutive_losses,
                },
                "market_dna": self.market_dna.get_global_stats(),
                "similarity_search": self.similarity_search.get_search_stats(),
                "bayesian_engine": self.bayesian_engine.get_calibration_report(),
                "ensemble_intelligence": self.ensemble_intelligence.get_model_report(),
                "online_learner": self.online_learner.get_learning_state(),
                "abstention_model": self.abstention_model.get_stats(),
                "meta_supervisor": {
                    "meta_report": self.meta_supervisor.get_meta_report().to_dict(),
                    "recommended_adjustments": self.meta_supervisor.get_recommended_adjustments(),
                },
                "capital_preservation": self.capital_preservation.get_risk_report(),
                "self_improvement": self.self_improvement.get_pipeline_stats(),
                "last_fingerprint": self._last_fingerprint.to_dict() if self._last_fingerprint else None,
                "last_anomaly": self._last_anomaly.to_dict() if self._last_anomaly else None,
                "last_explanation": self._last_explanation.to_dict() if self._last_explanation else None,
                "legacy": self._legacy.get_intelligence_state(),
            }
        except Exception as exc:
            logger.error("get_intelligence_state failed: %s", exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save_all(self):
        """Persist all component states to disk."""
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            self.market_dna.save(f"{self._data_dir}/market_dna.pkl")
            self.similarity_search.save(f"{self._data_dir}/similarity_search.pkl")
            self.bayesian_engine.save(f"{self._data_dir}/bayesian_engine.pkl")
            self.ensemble_intelligence.save(f"{self._data_dir}/ensemble_intelligence.pkl")
            self.online_learner.save(f"{self._data_dir}/online_learner.pkl")
            self.abstention_model.save(f"{self._data_dir}/abstention_model.pkl")
            self.meta_supervisor.save(f"{self._data_dir}/meta_supervisor.pkl")
            self.capital_preservation.save(f"{self._data_dir}/capital_preservation.pkl")
            self.self_improvement.save(f"{self._data_dir}/self_improvement.pkl")
            self._legacy.save_all()
            logger.info("All research components saved to %s", self._data_dir)
        except Exception as exc:
            logger.error("save_all failed: %s", exc)

    def load_all(self):
        """Load all component states from disk."""
        try:
            self.market_dna.load(f"{self._data_dir}/market_dna.pkl")
            self.similarity_search.load(f"{self._data_dir}/similarity_search.pkl")
            self.bayesian_engine.load(f"{self._data_dir}/bayesian_engine.pkl")
            self.ensemble_intelligence.load(f"{self._data_dir}/ensemble_intelligence.pkl")
            self.online_learner.load(f"{self._data_dir}/online_learner.pkl")
            self.abstention_model.load(f"{self._data_dir}/abstention_model.pkl")
            self.meta_supervisor.load(f"{self._data_dir}/meta_supervisor.pkl")
            self.capital_preservation.load(f"{self._data_dir}/capital_preservation.pkl")
            self.self_improvement.load(f"{self._data_dir}/self_improvement.pkl")
            self._legacy.load_all()
            logger.info("All research components loaded from %s", self._data_dir)
        except Exception as exc:
            logger.error("load_all failed: %s", exc)

    # ------------------------------------------------------------------
    # Research cycles
    # ------------------------------------------------------------------

    def run_research_cycle(self) -> ImprovementAttempt:
        """Periodic self-improvement cycle — archive, retrain, compare, promote."""
        logger.info("Starting research improvement cycle")
        attempt = self.self_improvement.run_improvement_cycle(
            description="Scheduled research improvement cycle",
        )
        if attempt.promoted:
            self.save_all()
        return attempt

    def get_backtest_report(
        self,
        trade_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run backtesting on historical trade records."""
        if not trade_records:
            return {"error": "No trade records provided"}

        result = self.backtesting_engine.run_backtest(trade_records)

        wf = None
        if len(trade_records) >= 200:
            wf = self.backtesting_engine.walk_forward_validation(trade_records)

        mc = None
        if len(trade_records) >= 30:
            mc = self.backtesting_engine.monte_carlo_permutation(trade_records)

        self.backtesting_engine.parameter_stability_check(
            trade_records,
            param_names=["confidence", "kelly_fraction"],
        )

        report_text = self.backtesting_engine.generate_report(result)
        val_stats = self.backtesting_engine.get_validation_stats()

        return {
            "result": result.to_dict(),
            "walk_forward": [w.to_dict() for w in wf] if wf else [],
            "monte_carlo_distribution": mc.tolist() if mc is not None else [],
            "validation_stats": val_stats,
            "report": report_text,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyzer_output_to_votes(self, analyzer_output: dict) -> List[ModelVote]:
        """Convert analyzer_output dict to list of ModelVote dataclasses."""
        votes: List[ModelVote] = []
        consensus = analyzer_output.get("consensus", {})
        direction = consensus.get("direction", "CALL")
        confidence_val = consensus.get("confidence", 50.0)
        n_models = max(consensus.get("n_total", 3), 1)

        # Create individual votes from sub-analyzers
        seen_models = set()
        for key in ("momentum", "mean_reversion", "pattern", "volatility", "ml"):
            sub = None
            if key in analyzer_output:
                sub = analyzer_output[key]
            elif "analyzers" in analyzer_output and isinstance(analyzer_output["analyzers"], dict):
                sub = analyzer_output["analyzers"].get(key)

            if sub and isinstance(sub, dict):
                name = sub.get("name", key)
                if name in seen_models:
                    continue
                seen_models.add(name)
                sub_dir = sub.get("direction", direction)
                sub_conf = float(sub.get("confidence", sub.get("score", 50.0)))
                votes.append(ModelVote(
                    model_name=name,
                    direction=sub_dir,
                    confidence=sub_conf,
                ))

        # Fallback: create synthetic votes from consensus
        if not votes:
            for i in range(n_models):
                model_name = f"analyzer_{i}"
                votes.append(ModelVote(
                    model_name=model_name,
                    direction=direction,
                    confidence=confidence_val * (0.8 + 0.2 * (i / max(n_models - 1, 1))),
                ))

        return votes

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
        prices = np.array(list(price_history)[-50:], dtype=np.float64)
        if len(prices) < 2:
            return 0.0
        returns = np.diff(np.log(np.maximum(prices, 1e-12)))
        return float(np.std(returns)) if len(returns) > 0 else 0.0

    @staticmethod
    def _extract_regime_str(analyzer_output: dict) -> str:
        regime = analyzer_output.get("regime", {})
        if isinstance(regime, dict):
            return regime.get("regime", regime.get("name", "UNKNOWN"))
        if hasattr(regime, "regime"):
            return regime.regime
        if isinstance(regime, str):
            return regime
        return "UNKNOWN"

    @staticmethod
    def _extract_regime_confidence(analyzer_output: dict) -> float:
        regime = analyzer_output.get("regime", {})
        if isinstance(regime, dict):
            return float(regime.get("confidence", 0.5))
        if hasattr(regime, "confidence"):
            return float(regime.confidence)
        return 0.5

    @staticmethod
    def _extract_analyzer_confidences(analyzer_output: dict) -> Dict[str, float]:
        """Extract per-analyzer confidence scores from analyzer_output."""
        confs: Dict[str, float] = {}
        for key in ("momentum", "mean_reversion", "pattern", "volatility", "ml"):
            sub = None
            if key in analyzer_output:
                sub = analyzer_output[key]
            elif "analyzers" in analyzer_output and isinstance(analyzer_output["analyzers"], dict):
                sub = analyzer_output["analyzers"].get(key)
            if sub and isinstance(sub, dict):
                name = sub.get("name", key)
                conf = float(sub.get("confidence", sub.get("score", 50.0)))
                confs[name] = conf
        if not confs:
            consensus = analyzer_output.get("consensus", {})
            confs["consensus"] = float(consensus.get("confidence", 50.0))
        return confs

    def _build_learning_features(
        self,
        fingerprint: DNAFingerprint,
        ensemble: EnsembleVerdict,
        bayesian: BayesianVerdict,
        price_history: list,
        digit_history: list,
    ) -> Dict[str, float]:
        return {
            "volatility": fingerprint.features.get("volatility", 0.0),
            "hurst": fingerprint.features.get("hurst", 0.5),
            "entropy": fingerprint.features.get("entropy", 0.0),
            "autocorrelation": fingerprint.features.get("autocorrelation", 0.0),
            "ensemble_conf": ensemble.confidence / 100.0,
            "ensemble_agreement": ensemble.agreement_ratio,
            "bayesian_mean": bayesian.overall_confidence,
            "bayesian_uncertainty": bayesian.uncertainty_remaining,
            "trend_strength": fingerprint.features.get("trend_strength", 0.0),
        }

    def _build_meta_state(self, analyzer_output: dict) -> Dict[str, Any]:
        """Build state dict for MetaSupervisor.supervise()."""
        total = self._tick_count
        return {
            "meta_ai": {
                "consensus": {
                    "win_rate": 0.5,
                    "avg_confidence_when_correct": 50.0,
                    "avg_confidence_when_wrong": 50.0,
                    "total_predictions": total,
                    "wrong": self._reject_count + self._abstain_count,
                    "profit_contribution": 0.0,
                },
            },
            "pipeline_stats": {
                "trades_recommended": self._trade_count,
                "abstentions": self._abstain_count,
                "rejections": self._reject_count,
                "avg_latency_ms": 10.0,
            },
        }

    def _compute_opportunity_score(
        self,
        bayesian: BayesianVerdict,
        ensemble: EnsembleVerdict,
        online_prediction: float,
    ) -> float:
        """Composite opportunity score from multiple modules."""
        score = (
            bayesian.overall_confidence * 40.0
            + (ensemble.confidence / 100.0) * 30.0
            + online_prediction * 30.0
        )
        return float(np.clip(score, 0.0, 100.0))

    def _estimate_win_rate(
        self,
        search_results: List[SearchResult],
        bayesian: BayesianVerdict,
        online_prediction: float,
    ) -> float:
        """Blend similarity search win rate with Bayesian and online estimates."""
        sim_wr = 0.5
        if search_results:
            wins = sum(1 for r in search_results if r.outcome == "WIN")
            sim_wr = wins / len(search_results)
        return float(np.clip(
            0.3 * sim_wr + 0.4 * bayesian.overall_confidence + 0.3 * online_prediction,
            0.01, 0.99,
        ))

    def _estimate_avg_win(self, search_results: List[SearchResult]) -> float:
        if not search_results:
            return 1.0
        wins = [r.profit for r in search_results if r.profit > 0]
        return float(np.mean(wins)) if wins else 1.0

    def _estimate_avg_loss(self, search_results: List[SearchResult]) -> float:
        if not search_results:
            return 1.0
        losses = [abs(r.profit) for r in search_results if r.profit < 0]
        return float(np.mean(losses)) if losses else 1.0

    def _get_drawdown(self) -> float:
        try:
            rr = self.capital_preservation.get_risk_report()
            return rr.get("drawdown", {}).get("current_pct", 0.0) / 100.0
        except Exception:
            return 0.0

    def _record_pipeline_state(
        self,
        decision: str,
        search_results: List[SearchResult],
        features: Dict[str, float],
    ) -> None:
        """Record pipeline outputs for internal tracking."""
        self._features_buffer.append(features)
        if len(self._features_buffer) > 500:
            self._features_buffer = self._features_buffer[-500:]

        # Index search result patterns that were useful
        for r in search_results[:3]:
            if r.similarity > 0.7:
                self.similarity_search.index_pattern(
                    record_id=f"query_{int(time.time())}_{r.record_id}",
                    features=r.features,
                    outcome=r.outcome,
                    profit=r.profit,
                    regime=r.regime,
                    market=r.market,
                )

    def _retrain_callback(self) -> Dict[str, float]:
        """Callback for SelfImprovementPipeline retraining."""
        try:
            # Attempt re-clustering
            drift_report = None
            if self._features_buffer:
                drift_report = self.online_learner.check_drift(
                    self._features_buffer[-1],
                )

            # Update meta weights
            weights = self.meta_supervisor.update_weights()

            return {
                "f1": self._compute_f1_metric(),
                "drift_magnitude": drift_report.magnitude if drift_report else 0.0,
                "calibration_error": self.meta_supervisor.get_meta_report().overall_calibration_error,
                "n_analyzers": len(weights),
                "abstention_accuracy": self.abstention_model.get_stats().get("abstention_quality_score", 0.5),
            }
        except Exception as exc:
            logger.error("Retrain callback failed: %s", exc)
            return {"f1": 0.0, "calibration_error": 1.0}

    def _metrics_callback(self) -> Dict[str, float]:
        """Callback for SelfImprovementPipeline metrics evaluation."""
        return {
            "f1": self._compute_f1_metric(),
            "calibration_error": self.meta_supervisor.get_meta_report().overall_calibration_error,
        }

    def _compute_f1_metric(self) -> float:
        """Compute a synthetic F1-like metric from pipeline performance."""
        total = self._trade_count + self._abstain_count + self._reject_count
        if total == 0:
            return 0.5
        precision = self._trade_count / max(total, 1)
        recall = 1.0 - (self._abstain_count / max(total, 1))
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    # ------------------------------------------------------------------
    # Mock objects for API compatibility
    # ------------------------------------------------------------------

    @staticmethod
    def _make_opportunity_score_obj(score: float):
        """Create a duck-typed opportunity score compatible with ExplainableEngine."""
        class _OppScore:
            def __init__(self, s):
                self.score = s
                self.components = {"composite": s}
                self._weights = {}
                self.recommendation = "TRADE" if s >= 60 else "ABSTAIN"
        return _OppScore(score)

    @staticmethod
    def _make_regime_obj(regime: str, confidence: float):
        """Create a duck-typed regime object compatible with ExplainableEngine."""
        class _Regime:
            def __init__(self, r, c):
                self.regime = r
                self.confidence = c
        return _Regime(regime, confidence)
