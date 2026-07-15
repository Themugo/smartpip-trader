"""
Comprehensive tests for the 12 advanced research intelligence modules.

Tests MarketDNA, SimilaritySearch, BayesianEngine, EnsembleIntelligence,
OnlineLearner, AbstentionModel, MetaSupervisor, ExplainableEngine,
BacktestingEngine, CapitalPreservation, SelfImprovementPipeline,
and ResearchOrchestrator.
"""
import os
import sys
import time
import math
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligence.market_dna import MarketDNA, DNAFingerprint, AnomalyReport, TransitionPrediction
from intelligence.similarity_search import SimilaritySearch, SearchResult
from intelligence.bayesian_engine import BayesianEngine, BayesianVerdict, PosteriorStats
from intelligence.ensemble_intelligence import EnsembleIntelligence, ModelVote, EnsembleVerdict
from intelligence.online_learner import OnlineLearner, DriftReport, LearningState
from intelligence.abstention_model import AbstentionModel, AbstentionVerdict, AbstentionSignal
from intelligence.meta_supervisor import MetaSupervisor, CalibrationReport, MetaReport, AnalyzerStats
from intelligence.explainable_engine import ExplainableEngine, StructuredExplanation, DecisionStep
from intelligence.backtesting_engine import BacktestingEngine, BacktestResult, WalkForwardWindow
from intelligence.capital_preservation import CapitalPreservation, RiskState, TradeDecision
from intelligence.self_improvement import SelfImprovementPipeline, ImprovementAttempt
from intelligence.research_orchestrator import ResearchOrchestrator


class _TempDirMixin:
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="sip_research_")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)


# =====================================================================
# 1. MarketDNA
# =====================================================================
class TestMarketDNA(_TempDirMixin, unittest.TestCase):

    def test_compute_fingerprint_basic(self):
        dna = MarketDNA()
        prices = [100 + i * 0.3 + np.random.normal(0, 0.05) for i in range(60)]
        digits = [int(str(abs(p))[-1]) for p in prices]
        fp = dna.compute_fingerprint("R_50", prices, digits)
        self.assertIsInstance(fp, DNAFingerprint)
        self.assertEqual(fp.market, "R_50")
        self.assertIn("volatility", fp.features)
        self.assertIn("entropy", fp.features)
        self.assertIn("hurst", fp.features)
        self.assertGreaterEqual(fp.cluster_id, 0)

    def test_compute_fingerprint_empty_data(self):
        dna = MarketDNA()
        fp = dna.compute_fingerprint("R_75", [], [])
        self.assertIsInstance(fp, DNAFingerprint)
        self.assertEqual(fp.market, "R_75")
        self.assertIn("volatility", fp.features)

    def test_detect_anomaly_no_history(self):
        dna = MarketDNA()
        fp = dna.compute_fingerprint("R_50", [100] * 30, [1, 2, 3] * 10)
        report = dna.detect_anomaly("R_50", fp)
        self.assertIsInstance(report, AnomalyReport)
        self.assertFalse(report.is_anomaly)
        self.assertEqual(len(report.contributing_features), 0)

    def test_detect_anomaly_with_history(self):
        dna = MarketDNA()
        for i in range(30):
            prices = [100 + i * 0.1 + np.random.normal(0, 0.01) for _ in range(50)]
            digits = [int(str(abs(p))[-1]) for p in prices]
            dna.compute_fingerprint("R_50", prices, digits)
        fp = dna.compute_fingerprint("R_50", [100 + np.random.normal(0, 10) for _ in range(50)], [5] * 50)
        report = dna.detect_anomaly("R_50", fp)
        self.assertIsInstance(report, AnomalyReport)
        self.assertIsInstance(report.is_anomaly, bool)

    def test_predict_transition_insufficient_data(self):
        dna = MarketDNA()
        pred = dna.predict_transition("R_50", "TRENDING_UP")
        self.assertIsInstance(pred, TransitionPrediction)
        self.assertEqual(pred.current_regime, "TRENDING_UP")
        self.assertIn(pred.predicted_regime, [
            "TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING",
            "RANDOM", "HIGH_VOLATILITY", "LOW_VOLATILITY",
        ])

    def test_predict_transition_with_history(self):
        dna = MarketDNA()
        regimes = ["TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING", "RANDOM",
                    "TRENDING_UP", "TRENDING_UP", "HIGH_VOLATILITY", "LOW_VOLATILITY"]
        for r in regimes:
            dna.predict_transition("R_50", r)
        pred = dna.predict_transition("R_50", "TRENDING_UP")
        self.assertIsInstance(pred, TransitionPrediction)
        self.assertGreater(pred.probability, 0.0)

    def test_get_market_profile(self):
        dna = MarketDNA()
        prices = [100 + i * 0.2 for i in range(40)]
        digits = [int(str(abs(p))[-1]) for p in prices]
        dna.compute_fingerprint("R_50", prices, digits)
        profile = dna.get_market_profile("R_50")
        self.assertIn("market", profile)
        self.assertEqual(profile["market"], "R_50")
        self.assertGreater(profile["fingerprints"], 0)
        self.assertIn("avg_features", profile)
        self.assertIn("clusters", profile)

    def test_get_market_profile_empty(self):
        dna = MarketDNA()
        profile = dna.get_market_profile("NONEXISTENT")
        self.assertEqual(profile["fingerprints"], 0)
        self.assertEqual(profile["avg_features"], {})

    def test_save_load(self):
        dna = MarketDNA()
        prices = [100 + i * 0.3 for i in range(50)]
        digits = [int(str(abs(p))[-1]) for p in prices]
        dna.compute_fingerprint("R_50", prices, digits)
        path = os.path.join(self._tmp, "dna.pkl")
        dna.save(path)
        dna2 = MarketDNA()
        result = dna2.load(path)
        self.assertTrue(result)
        stats = dna2.get_global_stats()
        self.assertIn("total_fingerprints", stats)
        self.assertIn("markets_tracked", stats)


# =====================================================================
# 2. SimilaritySearch
# =====================================================================
class TestSimilaritySearch(_TempDirMixin, unittest.TestCase):

    def test_index_and_search(self):
        engine = SimilaritySearch()
        features = {"volatility": 0.005, "momentum": 0.1, "complexity": 0.02,
                     "confidence": 0.8, "direction": 1.0, "hour_sin": 0.0,
                     "hour_cos": 1.0, "entropy": 2.5,
                     "regime_0": 1.0, "regime_1": 0.0, "regime_2": 0.0, "regime_3": 0.0}
        for i in range(20):
            engine.index_pattern(
                record_id=f"p{i}",
                features=features,
                outcome="WIN" if i % 3 != 0 else "LOSS",
                profit=0.5 if i % 3 != 0 else -0.3,
                regime="TRENDING_UP",
                market="R_50",
                timestamp=time.time() - i * 3600,
            )
        query_features = {"volatility": 0.004, "momentum": 0.12, "complexity": 0.03,
                          "confidence": 0.75, "direction": 1.0, "hour_sin": 0.1,
                          "hour_cos": 0.99, "entropy": 2.3,
                          "regime_0": 1.0, "regime_1": 0.0, "regime_2": 0.0, "regime_3": 0.0}
        results = engine.search(query_features, top_k=5)
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 5)
        for r in results:
            self.assertIsInstance(r, SearchResult)
            self.assertGreater(r.similarity, 0)

    def test_search_empty_index(self):
        engine = SimilaritySearch()
        results = engine.search({"volatility": 0.01}, top_k=5)
        self.assertEqual(len(results), 0)

    def test_search_cross_market(self):
        engine = SimilaritySearch()
        for i in range(15):
            engine.index_pattern(
                record_id=f"p{i}",
                features={"volatility": 0.005 + i * 0.001, "momentum": 0.1, "complexity": 0.02,
                           "confidence": 0.8, "direction": 1.0, "hour_sin": 0.0,
                           "hour_cos": 1.0, "entropy": 2.5,
                           "regime_0": 1.0, "regime_1": 0.0, "regime_2": 0.0, "regime_3": 0.0},
                outcome="WIN",
                profit=0.5,
                market="R_50" if i < 10 else "R_75",
                regime="TRENDING_UP",
            )
        results = engine.search_cross_market(
            {"volatility": 0.006, "momentum": 0.1, "complexity": 0.02,
             "confidence": 0.8, "direction": 1.0, "hour_sin": 0.0,
             "hour_cos": 1.0, "entropy": 2.5,
             "regime_0": 1.0, "regime_1": 0.0, "regime_2": 0.0, "regime_3": 0.0},
            source_market="R_50",
            top_k=5,
        )
        for r in results:
            self.assertNotEqual(r.market, "R_50")

    def test_get_outcome_statistics(self):
        engine = SimilaritySearch()
        stats = engine.get_outcome_statistics([])
        self.assertEqual(stats["count"], 0)
        self.assertEqual(stats["win_rate"], 0.0)

        results = [
            SearchResult("r1", "R_50", 0.9, {}, "WIN", 0.5, "TRENDING_UP", time.time()),
            SearchResult("r2", "R_50", 0.8, {}, "LOSS", -0.3, "RANDOM", time.time()),
        ]
        stats = engine.get_outcome_statistics(results)
        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["win_rate"], 0.5)

    def test_save_load(self):
        engine = SimilaritySearch()
        engine.index_pattern("p1", {"volatility": 0.01}, outcome="WIN", profit=0.5, market="R_50")
        path = os.path.join(self._tmp, "ss.pkl")
        engine.save(path)
        engine2 = SimilaritySearch()
        result = engine2.load(path)
        self.assertTrue(result)
        self.assertEqual(engine2._total_indexed, 1)


# =====================================================================
# 3. BayesianEngine
# =====================================================================
class TestBayesianEngine(_TempDirMixin, unittest.TestCase):

    def test_update_win(self):
        engine = BayesianEngine()
        engine.update(
            outcome=True,
            analyzer_confidences={"momentum": 80.0, "mean_reversion": 60.0},
            regime="TRENDING_UP",
            market="R_50",
        )
        report = engine.get_calibration_report()
        self.assertEqual(report["total_updates"], 1)

    def test_update_loss(self):
        engine = BayesianEngine()
        engine.update(outcome=False, regime="RANDOM", market="R_75")
        report = engine.get_calibration_report()
        self.assertEqual(report["total_updates"], 1)

    def test_evaluate_signal(self):
        engine = BayesianEngine()
        for _ in range(10):
            engine.update(outcome=True, analyzer_confidences={"momentum": 80}, regime="TRENDING_UP", market="R_50")
        verdict = engine.evaluate_signal(
            analyzer_confidences={"momentum": 85.0, "pattern": 70.0},
            regime="TRENDING_UP",
            market="R_50",
        )
        self.assertIsInstance(verdict, BayesianVerdict)
        self.assertGreaterEqual(verdict.overall_confidence, 0.0)
        self.assertLessEqual(verdict.overall_confidence, 1.0)
        self.assertIn(verdict.recommendation, [
            "HIGH_CONFIDENCE", "MODERATE", "LOW_CONFIDENCE", "INSUFFICIENT_DATA",
        ])

    def test_evaluate_signal_empty(self):
        engine = BayesianEngine()
        verdict = engine.evaluate_signal(analyzer_confidences={})
        self.assertIsInstance(verdict, BayesianVerdict)
        self.assertIn(verdict.recommendation, [
            "HIGH_CONFIDENCE", "MODERATE", "LOW_CONFIDENCE", "INSUFFICIENT_DATA",
        ])

    def test_get_posterior(self):
        engine = BayesianEngine()
        engine.update(outcome=True, analyzer_confidences={"m": 80}, regime="TRENDING_UP", market="R_50")
        posterior = engine.get_posterior("m|TRENDING_UP|R_50")
        self.assertIsInstance(posterior, PosteriorStats)
        self.assertGreater(posterior.mean, 0.0)

    def test_get_posterior_missing(self):
        engine = BayesianEngine()
        posterior = engine.get_posterior("nonexistent")
        self.assertIsNone(posterior)

    def test_get_global_posterior(self):
        engine = BayesianEngine()
        engine.update(outcome=True)
        engine.update(outcome=False)
        gp = engine.get_global_posterior()
        self.assertIsInstance(gp, PosteriorStats)
        self.assertAlmostEqual(gp.mean, 0.5, delta=0.1)

    def test_get_calibration_report(self):
        engine = BayesianEngine()
        report = engine.get_calibration_report()
        self.assertIn("total_updates", report)
        self.assertIn("global_posterior", report)
        self.assertIn("n_regimes", report)
        self.assertIn("n_analyzers", report)

    def test_save_load(self):
        engine = BayesianEngine()
        engine.update(outcome=True, analyzer_confidences={"m": 80}, regime="TRENDING_UP", market="R_50")
        path = os.path.join(self._tmp, "bayes.pkl")
        engine.save(path)
        engine2 = BayesianEngine()
        result = engine2.load(path)
        self.assertTrue(result)
        report = engine2.get_calibration_report()
        self.assertEqual(report["total_updates"], 1)


# =====================================================================
# 4. EnsembleIntelligence
# =====================================================================
class TestEnsembleIntelligence(_TempDirMixin, unittest.TestCase):

    def test_aggregate_consensus(self):
        ensemble = EnsembleIntelligence()
        votes = [
            ModelVote("momentum", "CALL", 80),
            ModelVote("pattern", "CALL", 75),
            ModelVote("mean_reversion", "CALL", 70),
        ]
        verdict = ensemble.aggregate(votes, regime="TRENDING_UP")
        self.assertIsInstance(verdict, EnsembleVerdict)
        self.assertEqual(verdict.direction, "CALL")
        self.assertGreater(verdict.confidence, 50)
        self.assertGreater(verdict.agreement_ratio, 0.8)

    def test_aggregate_split(self):
        ensemble = EnsembleIntelligence()
        votes = [
            ModelVote("momentum", "CALL", 80),
            ModelVote("pattern", "PUT", 80),
        ]
        verdict = ensemble.aggregate(votes, regime="RANDOM")
        self.assertIsInstance(verdict, EnsembleVerdict)
        self.assertIn(verdict.direction, ["CALL", "PUT"])
        self.assertTrue(verdict.disagreement_detected)

    def test_aggregate_empty(self):
        ensemble = EnsembleIntelligence()
        verdict = ensemble.aggregate([], regime="UNKNOWN")
        self.assertEqual(verdict.direction, "NEUTRAL")
        self.assertEqual(verdict.confidence, 0.0)

    def test_aggregate_single_vote(self):
        ensemble = EnsembleIntelligence()
        votes = [ModelVote("solitary", "CALL", 90)]
        verdict = ensemble.aggregate(votes)
        self.assertEqual(verdict.direction, "CALL")
        self.assertGreater(verdict.confidence, 0)

    def test_update_performance(self):
        ensemble = EnsembleIntelligence()
        ensemble.update_performance("momentum", correct=True, confidence=80, regime="TRENDING_UP")
        ensemble.update_performance("momentum", correct=False, confidence=75, regime="TRENDING_UP")
        report = ensemble.get_model_report()
        self.assertIn("momentum", report["models"])
        perf = report["models"]["momentum"]
        self.assertEqual(perf["total_predictions"], 2)
        self.assertEqual(perf["correct_predictions"], 1)
        self.assertAlmostEqual(perf["win_rate"], 0.5)

    def test_get_model_report(self):
        ensemble = EnsembleIntelligence()
        ensemble.aggregate([
            ModelVote("m1", "CALL", 80),
            ModelVote("m2", "PUT", 65),
        ])
        report = ensemble.get_model_report()
        self.assertIn("total_models", report)
        self.assertIn("total_aggregations", report)
        self.assertEqual(report["total_aggregations"], 1)

    def test_save_load(self):
        ensemble = EnsembleIntelligence()
        ensemble.aggregate([ModelVote("m1", "CALL", 80)])
        ensemble.update_performance("m1", correct=True, confidence=80)
        path = os.path.join(self._tmp, "ens.pkl")
        ensemble.save(path)
        ensemble2 = EnsembleIntelligence()
        result = ensemble2.load(path)
        self.assertTrue(result)
        report = ensemble2.get_model_report()
        self.assertEqual(report["total_aggregations"], 1)
        self.assertIn("m1", report["models"])


# =====================================================================
# 5. OnlineLearner
# =====================================================================
class TestOnlineLearner(_TempDirMixin, unittest.TestCase):

    def test_update(self):
        learner = OnlineLearner()
        features = {"volatility": 0.005, "entropy": 2.5, "hurst": 0.5}
        state = learner.update(features, outcome=True, confidence=80)
        self.assertIsInstance(state, LearningState)
        self.assertEqual(state.total_updates, 1)
        self.assertGreater(state.learning_rate, 0)

    def test_update_multiple(self):
        learner = OnlineLearner()
        for i in range(20):
            features = {"volatility": 0.005 + i * 0.001, "entropy": 2.0 + i * 0.1}
            learner.update(features, outcome=i % 3 != 0, confidence=75)
        state = learner.get_learning_state()
        self.assertEqual(state["total_updates"], 20)
        self.assertIn("learning_rate", state)
        self.assertIn("drift_events", state)

    def test_check_drift_insufficient_data(self):
        learner = OnlineLearner()
        report = learner.check_drift({"volatility": 0.005})
        self.assertIsInstance(report, DriftReport)
        self.assertFalse(report.drift_detected)

    def test_check_drift_with_data(self):
        learner = OnlineLearner()
        for i in range(50):
            learner.update({"volatility": 0.005, "entropy": 2.0}, outcome=True, confidence=80)
        report = learner.check_drift({"volatility": 0.005})
        self.assertIsInstance(report, DriftReport)

    def test_predict_with_uncertainty(self):
        learner = OnlineLearner()
        pred, unc = learner.predict_with_uncertainty({"volatility": 0.005})
        self.assertGreater(pred, 0.0)
        self.assertLess(pred, 1.0)
        self.assertGreater(unc, 0.0)

    def test_get_learning_state(self):
        learner = OnlineLearner()
        state = learner.get_learning_state()
        self.assertIn("total_updates", state)
        self.assertIn("learning_rate", state)
        self.assertIn("current_win_rate", state)
        self.assertIn("feature_importance", state)

    def test_save_load(self):
        learner = OnlineLearner()
        learner.update({"volatility": 0.005}, outcome=True, confidence=80)
        path = os.path.join(self._tmp, "ol.pkl")
        learner.save(path)
        learner2 = OnlineLearner()
        result = learner2.load(path)
        self.assertTrue(result)
        self.assertEqual(learner2._total_updates, 1)


# =====================================================================
# 6. AbstentionModel
# =====================================================================
class TestAbstentionModel(_TempDirMixin, unittest.TestCase):

    def test_evaluate_low_risk(self):
        model = AbstentionModel()
        verdict = model.evaluate(
            volatility=0.10,
            regime_confidence=0.85,
            model_agreement=0.90,
            opportunity_score=80.0,
            recent_drawdown=0.01,
            hour=14,
            entropy=1.5,
            consecutive_losses=0,
        )
        self.assertIsInstance(verdict, AbstentionVerdict)
        self.assertFalse(verdict.should_abstain)
        self.assertGreater(verdict.confidence_in_abstention, 0.0)
        self.assertIn("TRADE ALLOWED", verdict.recommendation)

    def test_evaluate_high_risk(self):
        model = AbstentionModel()
        verdict = model.evaluate(
            volatility=0.30,
            regime_confidence=0.25,
            model_agreement=0.30,
            opportunity_score=20.0,
            recent_drawdown=0.08,
            hour=3,
            entropy=3.2,
            consecutive_losses=5,
        )
        self.assertIsInstance(verdict, AbstentionVerdict)
        self.assertTrue(verdict.should_abstain)
        self.assertGreater(verdict.abstention_probability, 0.5)

    def test_evaluate_moderate(self):
        model = AbstentionModel()
        verdict = model.evaluate(
            volatility=0.18,
            regime_confidence=0.50,
            model_agreement=0.60,
            opportunity_score=50.0,
            recent_drawdown=0.03,
            hour=12,
            entropy=2.5,
            consecutive_losses=2,
        )
        self.assertIsInstance(verdict, AbstentionVerdict)
        self.assertIsInstance(verdict.should_abstain, bool)

    def test_record_outcome(self):
        model = AbstentionModel()
        model.record_outcome(abstained=True, trade_outcome="LOSS", profit=-0.5)
        model.record_outcome(abstained=False, trade_outcome="WIN", profit=1.0)
        stats = model.get_stats()
        self.assertIn("total_evaluations", stats)
        self.assertIn("abstention_rate", stats)

    def test_get_stats(self):
        model = AbstentionModel()
        stats = model.get_stats()
        self.assertIn("total_evaluations", stats)
        self.assertIn("current_threshold", stats)
        self.assertIn("weights", stats)
        self.assertIn("signal_frequency", stats)

    def test_save_load(self):
        model = AbstentionModel()
        model.evaluate(
            volatility=0.20, regime_confidence=0.50, model_agreement=0.60,
            opportunity_score=50.0, recent_drawdown=0.03, hour=10,
            entropy=2.0, consecutive_losses=1,
        )
        path = os.path.join(self._tmp, "abst.pkl")
        model.save(path)
        model2 = AbstentionModel()
        model2.load(path)
        stats = model2.get_stats()
        self.assertEqual(stats["total_evaluations"], 1)


# =====================================================================
# 7. MetaSupervisor
# =====================================================================
class TestMetaSupervisor(_TempDirMixin, unittest.TestCase):

    def _make_intelligence_state(self):
        return {
            "meta_ai": {
                "even_odd": {
                    "win_rate": 0.65,
                    "avg_confidence_when_correct": 80.0,
                    "avg_confidence_when_wrong": 55.0,
                    "total_predictions": 100,
                    "wrong": 35,
                    "profit_contribution": 15.0,
                },
                "digit_analysis": {
                    "win_rate": 0.45,
                    "avg_confidence_when_correct": 70.0,
                    "avg_confidence_when_wrong": 65.0,
                    "total_predictions": 80,
                    "wrong": 44,
                    "profit_contribution": -5.0,
                },
            },
            "pipeline_stats": {
                "trades_recommended": 50,
                "abstentions": 10,
                "rejections": 5,
                "avg_latency_ms": 25.0,
            },
        }

    def test_supervise(self):
        meta = MetaSupervisor()
        state = self._make_intelligence_state()
        reports = meta.supervise(state)
        self.assertIsInstance(reports, dict)
        self.assertIn("calibration", reports)
        self.assertIn("latency", reports)
        self.assertIn("false_positive_rate", reports)
        self.assertIn("profit_factor", reports)
        self.assertIsInstance(reports["calibration"], CalibrationReport)

    def test_update_weights(self):
        meta = MetaSupervisor()
        state = self._make_intelligence_state()
        meta.supervise(state)
        meta.supervise(state)
        meta.supervise(state)
        weights = meta.update_weights()
        self.assertIsInstance(weights, dict)
        self.assertIn("even_odd", weights)
        self.assertIn("digit_analysis", weights)
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_get_analyzer_report(self):
        meta = MetaSupervisor()
        state = self._make_intelligence_state()
        meta.supervise(state)
        report = meta.get_analyzer_report()
        self.assertIn("even_odd", report)
        self.assertIsInstance(report["even_odd"], AnalyzerStats)
        self.assertGreater(report["even_odd"].total_predictions, 0)

    def test_get_meta_report(self):
        meta = MetaSupervisor()
        state = self._make_intelligence_state()
        meta.supervise(state)
        report = meta.get_meta_report()
        self.assertIsInstance(report, MetaReport)
        self.assertIn(report.pipeline_health, ["HEALTHY", "DEGRADED", "UNHEALTHY"])
        self.assertGreaterEqual(report.active_analyzers, 0)

    def test_save_load(self):
        meta = MetaSupervisor()
        state = self._make_intelligence_state()
        meta.supervise(state)
        path = os.path.join(self._tmp, "meta.pkl")
        meta.save(path)
        meta2 = MetaSupervisor()
        result = meta2.load(path)
        self.assertTrue(result)
        report = meta2.get_meta_report()
        self.assertEqual(report.total_supervisions, 1)


# =====================================================================
# 8. ExplainableEngine
# =====================================================================
class TestExplainableEngine(_TempDirMixin, unittest.TestCase):

    def _make_explain_args(self):
        return {
            "analyzer_output": {
                "consensus": {"confidence": 85, "direction": "CALL", "n_agreeing": 8, "n_total": 10},
                "momentum": {"direction": "CALL", "confidence": 80},
                "pattern": {"direction": "CALL", "confidence": 75},
            },
            "opportunity_score": MagicMock(score=82, recommendation="TRADE",
                                           components={"consensus": 85, "entropy": 2.0},
                                           _weights={}),
            "regime": MagicMock(regime="TRENDING_UP", confidence=0.75),
            "trade_memory_stats": {"win_rate": 0.65, "total_trades": 100},
            "case_reasoner_output": {"win_rate_in_similar": 0.7, "recommendation": "TRADE",
                                     "similar_cases_count": 15},
            "rl_action": MagicMock(action="TRADE", confidence=0.65, q_values={"TRADE": 0.3}),
            "digital_twin_result": MagicMock(approved=True, simulated_win_rate=0.62),
            "risk_check": {"can_trade": True, "reason": ""},
            "bayesian_verdict": MagicMock(overall_confidence=0.72, recommendation="MODERATE"),
            "abstention_verdict": MagicMock(should_abstain=False, confidence=0.3),
            "ensemble_verdict": MagicMock(direction="CALL", confidence=75.0, agreement_ratio=0.8),
        }

    def test_explain_trade(self):
        engine = ExplainableEngine(db_path=os.path.join(self._tmp, "ee.db"))
        args = self._make_explain_args()
        explanation = engine.explain(**args)
        self.assertIsInstance(explanation, StructuredExplanation)
        self.assertIn(explanation.decision, ["TRADE", "ABSTAIN", "REJECT"])
        self.assertGreater(explanation.confidence, 0)
        self.assertGreater(len(explanation.factors), 0)
        self.assertGreater(len(explanation.decision_path), 0)

    def test_explain_abstain(self):
        engine = ExplainableEngine(db_path=os.path.join(self._tmp, "ee2.db"))
        args = self._make_explain_args()
        args["risk_check"] = {"can_trade": False, "reason": "Circuit breaker active"}
        explanation = engine.explain(**args)
        self.assertIn(explanation.decision, ["ABSTAIN", "REJECT"])

    def test_decompose_confidence(self):
        engine = ExplainableEngine(db_path=os.path.join(self._tmp, "ee3.db"))
        factors = [
            {"name": "consensus", "contribution": 20.0, "weight": 0.3},
            {"name": "entropy", "contribution": -5.0, "weight": 0.2},
            {"name": "regime", "contribution": 15.0, "weight": 0.1},
        ]
        decomp = engine.decompose_confidence(factors, 65.0)
        self.assertIn("consensus", decomp)
        self.assertIn("entropy", decomp)
        self.assertIn("_positive_sum", decomp)
        self.assertIn("_negative_sum", decomp)
        self.assertIn("_overall_score", decomp)

    def test_trace_decision_path(self):
        engine = ExplainableEngine(db_path=os.path.join(self._tmp, "ee4.db"))
        path = engine.trace_decision_path(
            overall_score=70.0, consensus_value=80.0,
            regime_name="TRENDING_UP", regime_confidence=0.75,
            twin_approved=True, twin_win_rate=62.0,
            risk_passed=True, risk_reason="",
            cbr_win_rate=65.0, rl_action_name="TRADE",
            bayes_conf=70.0, abstain_score=0.0,
        )
        self.assertIsInstance(path, list)
        self.assertGreater(len(path), 0)
        for step in path:
            self.assertIsInstance(step, DecisionStep)
            self.assertIn("step_name", step.to_dict())

    def test_generate_trade_report(self):
        engine = ExplainableEngine(db_path=os.path.join(self._tmp, "ee5.db"))
        args = self._make_explain_args()
        explanation = engine.explain(**args)
        report = engine.generate_trade_report(explanation)
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 100)
        self.assertIn("TRADE DECISION REPORT", report)

    def test_get_decision_stats(self):
        engine = ExplainableEngine(db_path=os.path.join(self._tmp, "ee6.db"))
        for _ in range(5):
            args = self._make_explain_args()
            engine.explain(**args)
        stats = engine.get_decision_stats()
        self.assertIn("total_explanations", stats)
        self.assertEqual(stats["total_explanations"], 5)
        self.assertIn("avg_score", stats)
        self.assertIn("avg_confidence", stats)


# =====================================================================
# 9. BacktestingEngine
# =====================================================================
class TestBacktestingEngine(_TempDirMixin, unittest.TestCase):

    def _make_trades(self, n=50):
        rng = np.random.default_rng(42)
        trades = []
        for i in range(n):
            pnl = float(rng.choice([-1.0, -0.5, 0.5, 1.0, 1.5]))
            trades.append({"pnl": pnl, "duration": float(rng.integers(1, 5))})
        return trades

    def test_run_backtest(self):
        engine = BacktestingEngine()
        trades = self._make_trades(50)
        result = engine.run_backtest(trades)
        self.assertIsInstance(result, BacktestResult)
        self.assertEqual(result.total_trades, 50)
        self.assertGreaterEqual(result.win_rate, 0.0)
        self.assertLessEqual(result.win_rate, 1.0)
        self.assertGreaterEqual(result.max_drawdown, 0.0)
        self.assertIsNotNone(result.equity_curve)

    def test_run_backtest_empty(self):
        engine = BacktestingEngine()
        result = engine.run_backtest([])
        self.assertEqual(result.total_trades, 0)

    def test_walk_forward_validation(self):
        engine = BacktestingEngine(walk_train_bars=20, walk_test_bars=10)
        trades = self._make_trades(100)
        windows = engine.walk_forward_validation(trades)
        self.assertIsInstance(windows, list)
        self.assertGreater(len(windows), 0)
        for w in windows:
            self.assertIsInstance(w, WalkForwardWindow)
            self.assertGreaterEqual(w.train_win_rate, 0.0)
            self.assertLessEqual(w.train_win_rate, 1.0)

    def test_walk_forward_insufficient_data(self):
        engine = BacktestingEngine(walk_train_bars=50, walk_test_bars=50)
        trades = self._make_trades(20)
        windows = engine.walk_forward_validation(trades)
        self.assertEqual(len(windows), 0)

    def test_monte_carlo_permutation(self):
        engine = BacktestingEngine(monte_carlo_runs=50)
        trades = self._make_trades(30)
        distribution = engine.monte_carlo_permutation(trades, seed=42)
        self.assertEqual(len(distribution), 50)

    def test_monte_carlo_insufficient_data(self):
        engine = BacktestingEngine()
        trades = self._make_trades(3)
        distribution = engine.monte_carlo_permutation(trades)
        self.assertEqual(len(distribution), 0)

    def test_generate_report(self):
        engine = BacktestingEngine()
        trades = self._make_trades(30)
        result = engine.run_backtest(trades)
        report = engine.generate_report(result)
        self.assertIsInstance(report, str)
        self.assertIn("BACKTEST REPORT", report)
        self.assertIn("Win Rate", report)

    def test_generate_report_no_data(self):
        engine = BacktestingEngine()
        report = engine.generate_report()
        self.assertEqual(report, "No backtest results available.")

    def test_save_load(self):
        engine = BacktestingEngine()
        trades = self._make_trades(30)
        engine.run_backtest(trades)
        path = os.path.join(self._tmp, "bt.pkl")
        engine.save(path)
        engine2 = BacktestingEngine.load(path)
        self.assertIsNotNone(engine2._last_backtest)
        self.assertEqual(engine2._last_backtest.total_trades, 30)


# =====================================================================
# 10. CapitalPreservation
# =====================================================================
class TestCapitalPreservation(_TempDirMixin, unittest.TestCase):

    def test_evaluate_risk_fresh(self):
        cp = CapitalPreservation()
        state = cp.evaluate_risk()
        self.assertIsInstance(state, RiskState)
        self.assertEqual(state.risk_level, "LOW")
        self.assertEqual(state.consecutive_losses, 0)
        self.assertGreater(state.max_position_size, 0)

    def test_calculate_position_size(self):
        cp = CapitalPreservation()
        result = cp.calculate_position_size(
            win_rate=0.60, avg_win=1.5, avg_loss=1.0,
            confidence=80.0, regime="TRENDING_UP",
        )
        self.assertIn("amount", result)
        self.assertGreater(result["amount"], 0)
        self.assertIn("kelly_raw", result)
        self.assertIn("multipliers", result)

    def test_should_allow_trade_clean(self):
        cp = CapitalPreservation()
        decision = cp.should_allow_trade(confidence=75.0)
        self.assertIsInstance(decision, TradeDecision)
        self.assertTrue(decision.allowed)

    def test_should_allow_trade_rate_limit(self):
        cp = CapitalPreservation(max_trades_per_hour=2)
        cp.update_after_trade(1.0)
        cp.update_after_trade(1.0)
        cp.update_after_trade(1.0)
        decision = cp.should_allow_trade()
        self.assertFalse(decision.allowed)
        self.assertIn("Rate limit", decision.reason)

    def test_update_after_trade_win(self):
        cp = CapitalPreservation()
        initial_balance = cp._balance
        cp.update_after_trade(5.0)
        self.assertGreater(cp._balance, initial_balance)
        self.assertEqual(cp._consec_losses, 0)
        self.assertGreater(cp._trades_today, 0)

    def test_update_after_trade_loss(self):
        cp = CapitalPreservation()
        cp.update_after_trade(-1.0)
        self.assertEqual(cp._consec_losses, 1)
        cp.update_after_trade(-1.0)
        self.assertEqual(cp._consec_losses, 2)

    def test_consecutive_losses_cooldown(self):
        cp = CapitalPreservation()
        for _ in range(6):
            cp.update_after_trade(-1.0)
        decision = cp.should_allow_trade()
        self.assertFalse(decision.allowed)

    def test_get_risk_report(self):
        cp = CapitalPreservation()
        report = cp.get_risk_report()
        self.assertIn("risk_state", report)
        self.assertIn("limits", report)
        self.assertIn("balance", report)
        self.assertIn("drawdown", report)
        self.assertIn("trade_frequency", report)
        self.assertIn("kelly", report)
        self.assertIn("circuit_breaker", report)

    def test_save_load(self):
        cp = CapitalPreservation()
        cp.update_after_trade(5.0)
        cp.update_after_trade(-2.0)
        path = os.path.join(self._tmp, "cp.pkl")
        cp.save(path)
        cp2 = CapitalPreservation()
        result = cp2.load(path)
        self.assertTrue(result)
        self.assertEqual(cp2._trades_today, 2)


# =====================================================================
# 11. SelfImprovementPipeline
# =====================================================================
class TestSelfImprovementPipeline(_TempDirMixin, unittest.TestCase):

    def _make_pipeline(self):
        archive_dir = os.path.join(self._tmp, "archives")
        component_file = os.path.join(self._tmp, "model.joblib")
        import joblib as _jl
        _jl.dump({"version": 1}, component_file)

        metrics_fn = MagicMock(return_value={"f1": 0.65, "precision": 0.70})
        retrain_fn = MagicMock(return_value={"f1": 0.68, "precision": 0.72})

        sentinel = os.path.join(self._tmp, "_no_stale_state.joblib")
        with patch("intelligence.self_improvement._STATE_FILE", sentinel):
            pipeline = SelfImprovementPipeline(
                component_paths={"model": component_file},
                retrain_fn=retrain_fn,
                metrics_fn=metrics_fn,
                archive_dir=archive_dir,
            )
        return pipeline

    def test_archive_current(self):
        pipeline = self._make_pipeline()
        version_id = pipeline.archive_current()
        self.assertIsInstance(version_id, str)
        self.assertTrue(version_id.startswith("v"))
        self.assertEqual(pipeline._current_version_id, version_id)

    def test_compare_versions(self):
        pipeline = self._make_pipeline()
        v1 = pipeline.archive_current()
        pipeline._version_metrics[v1] = {"f1": 0.60}
        pipeline._last_known_metrics = {"f1": 0.60}
        v2 = pipeline.archive_current()
        pipeline._version_metrics[v2] = {"f1": 0.70}
        improvement = pipeline.compare_versions(v1, v2)
        self.assertGreater(improvement, 0)

    def test_promote_version(self):
        pipeline = self._make_pipeline()
        v1 = pipeline.archive_current()
        pipeline._version_metrics[v1] = {"f1": 0.65}
        pipeline._last_known_metrics = {"f1": 0.65}
        result = pipeline.promote_version(v1)
        self.assertTrue(result)
        self.assertEqual(pipeline._current_version_id, v1)

    def test_promote_nonexistent(self):
        pipeline = self._make_pipeline()
        result = pipeline.promote_version("nonexistent_version")
        self.assertFalse(result)

    def test_rollback(self):
        pipeline = self._make_pipeline()
        v1 = pipeline.archive_current()
        pipeline._version_metrics[v1] = {"f1": 0.60}
        pipeline._last_known_metrics = {"f1": 0.60}
        v2 = pipeline.archive_current()
        pipeline._version_metrics[v2] = {"f1": 0.65}
        pipeline._last_known_metrics = {"f1": 0.65}
        result = pipeline.rollback(v1)
        self.assertTrue(result)

    def test_run_improvement_cycle(self):
        pipeline = self._make_pipeline()
        attempt = pipeline.run_improvement_cycle(description="Test cycle")
        self.assertIsInstance(attempt, ImprovementAttempt)
        self.assertIn("cycle_", attempt.attempt_id)
        self.assertIn("f1", attempt.metrics_before)

    def test_get_pipeline_stats(self):
        pipeline = self._make_pipeline()
        pipeline.run_improvement_cycle()
        stats = pipeline.get_pipeline_stats()
        self.assertIn("total_attempts", stats)
        self.assertIn("promoted_count", stats)
        self.assertIn("current_version_id", stats)
        self.assertIn("primary_metric", stats)
        self.assertEqual(stats["total_attempts"], 1)

    def test_save_load(self):
        pipeline = self._make_pipeline()
        pipeline.run_improvement_cycle()
        path = os.path.join(self._tmp, "pipeline_state.pkl")
        pipeline.save(path)
        pipeline2 = self._make_pipeline()
        result = pipeline2.load(path)
        self.assertTrue(result)
        stats = pipeline2.get_pipeline_stats()
        self.assertEqual(stats["total_attempts"], 1)


# =====================================================================
# 12. ResearchOrchestrator
# =====================================================================
class TestResearchOrchestrator(_TempDirMixin, unittest.TestCase):

    def _make_orchestrator(self):
        settings = MagicMock(
            intelligence_enabled=True,
            min_opportunity_score=75,
            min_twin_win_rate=0.55,
            base_amount=1.0,
            kelly_fraction=0.25,
        )
        return ResearchOrchestrator(
            analysis_manager=None,
            settings=settings,
            data_dir=self._tmp,
        )

    def test_evaluate_tick(self):
        orch = self._make_orchestrator()
        result = orch.evaluate_tick(
            price_history=[100 + i * 0.3 + np.random.normal(0, 0.1) for i in range(50)],
            digit_history=[1, 3, 5, 7, 2, 4, 6, 8, 0, 1] * 2,
            analyzer_output={
                "consensus": {"confidence": 80, "direction": "CALL", "n_agreeing": 8, "n_total": 10},
                "entropy": 2.0,
                "regime": {"regime": "TRENDING_UP", "confidence": 0.7},
            },
            market="R_50",
            hour=14,
        )
        self.assertIn("decision", result)
        self.assertIn(result["decision"], ["TRADE", "ABSTAIN", "REJECT"])
        self.assertIn("score", result)
        self.assertIn("explanation", result)
        self.assertTrue(orch._tick_count >= 1)

    def test_evaluate_tick_multiple(self):
        orch = self._make_orchestrator()
        for i in range(5):
            orch.evaluate_tick(
                price_history=[100 + j * 0.2 for j in range(30)],
                digit_history=[i % 10, (i + 1) % 10] * 10,
                analyzer_output={
                    "consensus": {"confidence": 75 + i, "direction": "CALL", "n_agreeing": 7, "n_total": 10},
                },
                market="R_50",
                hour=14,
            )
        state = orch.get_intelligence_state()
        self.assertIn("research_orchestrator", state)
        self.assertEqual(state["research_orchestrator"]["ticks_evaluated"], 5)

    def test_get_intelligence_state(self):
        orch = self._make_orchestrator()
        state = orch.get_intelligence_state()
        self.assertIn("research_orchestrator", state)
        self.assertIn("market_dna", state)
        self.assertIn("similarity_search", state)
        self.assertIn("bayesian_engine", state)
        self.assertIn("ensemble_intelligence", state)
        self.assertIn("online_learner", state)
        self.assertIn("abstention_model", state)
        self.assertIn("meta_supervisor", state)
        self.assertIn("capital_preservation", state)
        self.assertIn("self_improvement", state)
        self.assertIn("legacy", state)

    def test_record_trade_outcome(self):
        orch = self._make_orchestrator()
        orch.evaluate_tick(
            price_history=[100 + i * 0.1 for i in range(40)],
            digit_history=[1, 3, 5, 7, 2] * 4,
            analyzer_output={
                "consensus": {"confidence": 80, "direction": "CALL", "n_agreeing": 8, "n_total": 10},
            },
            market="R_50",
            hour=14,
        )
        trade_record = MagicMock(
            profit=1.5,
            outcome="WIN",
            market="R_50",
        )
        orch._legacy.record_trade_outcome = MagicMock()
        orch.record_trade_outcome(trade_record, {"consensus": {"confidence": 80}})
        orch._legacy.record_trade_outcome.assert_called_once()

    def test_save_all_load_all(self):
        orch = self._make_orchestrator()
        orch.evaluate_tick(
            price_history=[100 + i * 0.2 for i in range(30)],
            digit_history=[1, 2, 3] * 5,
            analyzer_output={
                "consensus": {"confidence": 80, "direction": "CALL", "n_agreeing": 8, "n_total": 10},
            },
            market="R_50",
            hour=14,
        )
        orch.save_all()
        orch2 = self._make_orchestrator()
        orch2.load_all()
        state = orch2.get_intelligence_state()
        self.assertIn("research_orchestrator", state)
        self.assertIn("market_dna", state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
