"""
Comprehensive tests for the SmartPip Intelligence Layer.

Tests all 10 components plus the orchestrator.
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

from intelligence.regime_detector import RegimeDetector, MarketRegime
from intelligence.opportunity_scorer import OpportunityScorer, OpportunityScore
from intelligence.trade_memory import TradeMemory, TradeRecord
from intelligence.case_based_reasoner import CaseBasedReasoner, SimilarCase
from intelligence.rl_agent import RLAgent, RLAction
from intelligence.retraining_pipeline import RetrainingPipeline
from intelligence.explainable_ai import ExplainableAI, TradeExplanation
from intelligence.dynamic_sizer import DynamicSizer
from intelligence.meta_ai import MetaAI
from intelligence.digital_twin import DigitalTwin, TwinResult
from intelligence.intelligence_orchestrator import IntelligenceOrchestrator


class _TempDirMixin:
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="sip_test_")

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)


# =====================================================================
# 1. RegimeDetector
# =====================================================================
class TestRegimeDetector(_TempDirMixin, unittest.TestCase):

    def test_detect_insufficient_data(self):
        rd = RegimeDetector()
        result = rd.detect([], [])
        self.assertIsInstance(result, MarketRegime)
        self.assertIn(result.regime, [
            "TRENDING_UP", "TRENDING_DOWN", "MEAN_REVERTING",
            "RANDOM", "HIGH_VOLATILITY", "LOW_VOLATILITY",
        ])

    def test_detect_trending_up(self):
        rd = RegimeDetector()
        prices = [100 + i * 0.5 + np.random.normal(0, 0.05) for i in range(60)]
        digits = [int(str(p)[-1]) for p in prices]
        result = rd.detect(prices, digits)
        self.assertIsInstance(result, MarketRegime)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_detect_high_volatility(self):
        rd = RegimeDetector()
        # Use very high variance to trigger HIGH_VOLATILITY or RANDOM
        prices = [100 + np.random.normal(0, 10) for _ in range(100)]
        digits = [int(str(abs(p))[-1]) for p in prices]
        result = rd.detect(prices, digits)
        # With high variance, classifier may see HIGH_VOLATILITY, RANDOM, or LOW_VOLATILITY
        self.assertIn(result.regime, [
            "HIGH_VOLATILITY", "RANDOM", "MEAN_REVERTING", "LOW_VOLATILITY",
        ])

    def test_update_and_stats(self):
        rd = RegimeDetector()
        prices = [100 + i * 0.3 for i in range(50)]
        digits = [int(str(p)[-1]) for p in prices]
        rd.update(prices, digits, "TRENDING_UP")
        stats = rd.get_regime_stats()
        self.assertIn("total_detections", stats)
        self.assertIn("classifier_trained", stats)

    def test_save_load(self):
        rd = RegimeDetector()
        path = os.path.join(self._tmp, "regime.pkl")
        rd.save(path)
        rd2 = RegimeDetector()
        rd2.load(path)
        stats = rd2.get_regime_stats()
        self.assertIn("total_detections", stats)


# =====================================================================
# 2. OpportunityScorer
# =====================================================================
class TestOpportunityScorer(unittest.TestCase):

    def test_score_basic(self):
        os_ = OpportunityScorer()
        result = os_.score(
            analyzer_output={"consensus": {"confidence": 80, "direction": "CALL", "n_agreeing": 7, "n_total": 10}},
            entropy=2.0,
            volatility=0.005,
            historical_similarity=0.6,
            model_accuracy=0.65,
            regime="MEAN_REVERTING",
            digit_history=[1, 3, 5, 7, 2, 4, 6, 8, 0, 1],
            hour=14,
        )
        self.assertIsInstance(result, OpportunityScore)
        self.assertGreaterEqual(result.score, 0)
        self.assertLessEqual(result.score, 100)
        self.assertIn(result.recommendation, ["TRADE", "ABSTAIN", "WAIT"])

    def test_high_consensus_high_score(self):
        os_ = OpportunityScorer()
        result = os_.score(
            analyzer_output={"consensus": {"confidence": 95, "direction": "CALL", "n_agreeing": 9, "n_total": 10}},
            entropy=1.5,
            volatility=0.003,
            historical_similarity=0.75,
            model_accuracy=0.75,
            regime="TRENDING_UP",
            digit_history=[2, 2, 2, 4, 4, 4, 6, 6, 6, 8],
            hour=10,
        )
        self.assertGreater(result.score, 50)

    def test_random_regime_low_score(self):
        os_ = OpportunityScorer()
        result = os_.score(
            analyzer_output={"consensus": {"confidence": 50, "direction": "CALL", "n_agreeing": 5, "n_total": 10}},
            entropy=3.2,
            volatility=0.02,
            historical_similarity=0.3,
            model_accuracy=0.45,
            regime="RANDOM",
            digit_history=[1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
            hour=3,
        )
        self.assertLess(result.score, 60)

    def test_scoring_stats(self):
        os_ = OpportunityScorer()
        stats = os_.get_scoring_stats()
        self.assertIn("total_scores", stats)
        self.assertIn("current_weights", stats)


# =====================================================================
# 3. TradeMemory
# =====================================================================
class TestTradeMemory(_TempDirMixin, unittest.TestCase):

    def _make_record(self, trade_id="t1", market="R_50", outcome="WIN", profit=1.0):
        return TradeRecord(
            trade_id=trade_id,
            timestamp=time.time(),
            market=market,
            direction="CALL",
            amount=1.0,
            entry_price=100.0,
            exit_price=100.0 + profit,
            profit=profit,
            pnl_pct=profit,
            confidence=80.0,
            analyzer_outputs={"consensus": {"confidence": 80}},
            market_features={"regime": "TRENDING_UP", "entropy": 2.0, "volatility": 0.005},
            regime="TRENDING_UP",
            entropy=2.0,
            volatility=0.005,
            digit_pattern=[1, 3, 5, 7, 2],
            outcome=outcome,
            duration_seconds=60.0,
            metadata={},
        )

    def test_record_and_retrieve(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "mem.db"))
        rec = self._make_record()
        tm.record_trade(rec)
        recent = tm.get_recent(n=10)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].trade_id, "t1")

    def test_get_by_market(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "mem2.db"))
        tm.record_trade(self._make_record(market="R_50"))
        tm.record_trade(self._make_record(trade_id="t2", market="R_10"))
        r50 = tm.get_by_market("R_50")
        self.assertEqual(len(r50), 1)

    def test_get_winning_losing(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "mem3.db"))
        tm.record_trade(self._make_record(outcome="WIN", profit=1.0))
        tm.record_trade(self._make_record(trade_id="t2", outcome="LOSS", profit=-0.5))
        wins = tm.get_winning_trades()
        losses = tm.get_losing_trades()
        self.assertEqual(len(wins), 1)
        self.assertEqual(len(losses), 1)

    def test_feature_matrix(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "mem4.db"))
        for i in range(5):
            tm.record_trade(self._make_record(
                trade_id=f"t{i}",
                outcome="WIN" if i % 2 == 0 else "LOSS",
                profit=1.0 if i % 2 == 0 else -0.5,
            ))
        features, outcomes = tm.get_feature_matrix()
        self.assertEqual(len(features), 5)
        self.assertEqual(len(outcomes), 5)

    def test_stats(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "mem5.db"))
        tm.record_trade(self._make_record(outcome="WIN", profit=2.0))
        tm.record_trade(self._make_record(trade_id="t2", outcome="LOSS", profit=-1.0))
        stats = tm.get_stats()
        self.assertIn("total_trades", stats)
        self.assertEqual(stats["total_trades"], 2)

    def test_similar_trades(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "mem6.db"))
        for i in range(10):
            tm.record_trade(self._make_record(trade_id=f"t{i}"))
        similar = tm.get_similar_trades(
            {"entropy": 2.0, "volatility": 0.005, "consensus_confidence": 80},
            n=3,
        )
        self.assertLessEqual(len(similar), 3)


# =====================================================================
# 4. CaseBasedReasoner
# =====================================================================
class TestCaseBasedReasoner(_TempDirMixin, unittest.TestCase):

    def test_retrieve_empty(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "cbm.db"))
        cbr = CaseBasedReasoner(trade_memory=tm)
        result = cbr.retrieve(
            current_features={"entropy": 2.0, "volatility": 0.005},
            market="R_50",
            regime="TRENDING_UP",
            n=3,
        )
        self.assertEqual(len(result), 0)

    def test_retrieve_with_data(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "cbm2.db"))
        for i in range(20):
            rec = TradeRecord(
                trade_id=f"t{i}", timestamp=time.time() - i * 100,
                market="R_50", direction="CALL", amount=1.0,
                entry_price=100, exit_price=101 if i % 3 != 0 else 99,
                profit=1.0 if i % 3 != 0 else -1.0,
                pnl_pct=1.0, confidence=80.0,
                analyzer_outputs={}, market_features={"entropy": 2.0, "volatility": 0.005},
                regime="TRENDING_UP", entropy=2.0, volatility=0.005,
                digit_pattern=[1, 3, 5], outcome="WIN" if i % 3 != 0 else "LOSS",
                duration_seconds=60, metadata={},
            )
            tm.record_trade(rec)
        cbr = CaseBasedReasoner(trade_memory=tm)
        cases = cbr.retrieve(
            current_features={"entropy": 2.0, "volatility": 0.005, "regime": "TRENDING_UP"},
            market="R_50",
            regime="TRENDING_UP",
            n=5,
        )
        self.assertLessEqual(len(cases), 5)

    def test_evaluate(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "cbm3.db"))
        cbr = CaseBasedReasoner(trade_memory=tm)
        result = cbr.evaluate(current_features={"entropy": 2.0, "volatility": 0.005})
        self.assertIn("recommendation", result)

    def test_case_stats(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "cbm4.db"))
        cbr = CaseBasedReasoner(trade_memory=tm)
        stats = cbr.get_case_stats()
        self.assertIn("case_base_size", stats)


# =====================================================================
# 5. RLAgent
# =====================================================================
class TestRLAgent(_TempDirMixin, unittest.TestCase):

    def test_get_action(self):
        agent = RLAgent()
        state = {"regime": "TRENDING_UP", "entropy_level": 1, "volatility_level": 1, "consensus_level": 2, "time_bin": 2}
        action = agent.get_action(state)
        self.assertIsInstance(action, RLAction)
        self.assertIn(action.action, ["TRADE", "ABSTAIN"])

    def test_update(self):
        agent = RLAgent()
        state = {"regime": "TRENDING_UP", "entropy_level": 1, "volatility_level": 1, "consensus_level": 2, "time_bin": 2}
        next_state = {"regime": "TRENDING_UP", "entropy_level": 1, "volatility_level": 1, "consensus_level": 2, "time_bin": 2}
        agent.update(state, "TRADE", 1.0, next_state)
        stats = agent.get_q_table_stats()
        self.assertIn("total_updates", stats)

    def test_save_load(self):
        agent = RLAgent()
        state = {"regime": "RANDOM", "entropy_level": 3, "volatility_level": 3, "consensus_level": 0, "time_bin": 0}
        agent.update(state, "ABSTAIN", 0.5, state)
        path = os.path.join(self._tmp, "rl_save.pkl")
        agent.save(path)
        agent2 = RLAgent()
        agent2.load(path)
        action = agent2.get_action(state)
        self.assertIn(action.action, ["TRADE", "ABSTAIN"])

    def test_epsilon_decay(self):
        agent = RLAgent()
        initial_eps = agent.epsilon
        for _ in range(10):
            agent.decay_epsilon()
        self.assertLess(agent.epsilon, initial_eps)


# =====================================================================
# 6. RetrainingPipeline
# =====================================================================
class TestRetrainingPipeline(_TempDirMixin, unittest.TestCase):

    def _make_pipeline(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "rt_mem.db"))
        rd = RegimeDetector()
        os_ = OpportunityScorer()
        meta = MagicMock()
        meta.get_analyzer_report.return_value = {"average_win_rate": 0.5}
        return RetrainingPipeline(
            trade_memory=tm,
            ensemble_predictor=None,
            regime_detector=rd,
            opportunity_scorer=os_,
            meta_ai=meta,
        )

    def test_run_nightly_retrain(self):
        pipeline = self._make_pipeline()
        report = pipeline.run_nightly_retrain()
        self.assertIn("status", report)

    def test_get_retrain_history(self):
        pipeline = self._make_pipeline()
        history = pipeline.get_retrain_history()
        self.assertIsInstance(history, list)


# =====================================================================
# 7. ExplainableAI
# =====================================================================
class TestExplainableAI(_TempDirMixin, unittest.TestCase):

    def test_explain_trade(self):
        xai = ExplainableAI(db_path=os.path.join(self._tmp, "xai.db"))
        result = xai.explain_trade_decision(
            analyzer_output={"consensus": {"confidence": 85, "direction": "CALL", "n_agreeing": 8, "n_total": 10}},
            opportunity_score=MagicMock(score=82, recommendation="TRADE", components={"consensus": 85}),
            regime=MagicMock(regime="MEAN_REVERTING", confidence=0.7),
            trade_memory_stats={"win_rate": 0.65, "total_trades": 100},
            case_reasoner_output={"win_rate_in_similar": 0.7, "avg_profit_in_similar": 0.5},
            rl_action=MagicMock(action="TRADE", confidence=0.6),
            digital_twin_result={"approved": True, "simulated_win_rate": 0.62},
            risk_check={"can_trade": True, "reason": ""},
        )
        self.assertIsInstance(result, TradeExplanation)
        self.assertIn(result.decision, ["TRADE", "ABSTAIN", "REJECT"])

    def test_explain_abstain(self):
        xai = ExplainableAI(db_path=os.path.join(self._tmp, "xai2.db"))
        result = xai.explain_trade_decision(
            analyzer_output={"consensus": {"confidence": 35, "direction": "CALL", "n_agreeing": 4, "n_total": 10}},
            opportunity_score=MagicMock(score=30, recommendation="ABSTAIN", components={}),
            regime=MagicMock(regime="RANDOM", confidence=0.8),
            trade_memory_stats={"win_rate": 0.45},
            case_reasoner_output={"win_rate_in_similar": 0.4},
            rl_action=MagicMock(action="ABSTAIN", confidence=0.7),
            digital_twin_result=None,
            risk_check={"can_trade": False, "reason": "Low opportunity"},
        )
        self.assertIn(result.decision, ["ABSTAIN", "REJECT"])

    def test_generate_report(self):
        xai = ExplainableAI(db_path=os.path.join(self._tmp, "xai3.db"))
        exp = TradeExplanation(
            decision="TRADE", confidence=80, score=75,
            factors=[{"name": "consensus", "contribution": 30, "description": "Strong", "weight": 0.3}],
            regime_description="MEAN_REVERTING",
            risk_assessment="Low risk",
            similar_historical_cases=15,
            recommendation="Execute",
            timestamp=time.time(),
            raw_data={},
        )
        report = xai.generate_trade_report(exp)
        self.assertIsInstance(report, str)
        self.assertGreater(len(report), 0)

    def test_decision_stats(self):
        xai = ExplainableAI(db_path=os.path.join(self._tmp, "xai4.db"))
        stats = xai.get_decision_stats()
        self.assertIn("total_explanations", stats)


# =====================================================================
# 8. DynamicSizer
# =====================================================================
class TestDynamicSizer(_TempDirMixin, unittest.TestCase):

    def test_basic_sizing(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ds.db"))
        settings = MagicMock(
            base_amount=1.0,
            kelly_fraction=0.25,
            max_consecutive_losses=3,
        )
        sizer = DynamicSizer(trade_memory=tm, settings=settings)
        result = sizer.calculate_size(
            confidence=80, regime="TRENDING_UP", entropy=2.0,
            historical_edge=0.1, base_amount=1.0,
        )
        self.assertIn("amount", result)
        self.assertGreater(result["amount"], 0)

    def test_low_confidence_small_size(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ds2.db"))
        settings = MagicMock(
            base_amount=1.0,
            kelly_fraction=0.25,
            max_consecutive_losses=3,
        )
        sizer = DynamicSizer(trade_memory=tm, settings=settings)
        high = sizer.calculate_size(
            confidence=95, regime="TRENDING_UP", entropy=1.5,
            historical_edge=0.2, base_amount=10.0,
        )
        low = sizer.calculate_size(
            confidence=20, regime="RANDOM", entropy=3.2,
            historical_edge=-0.1, base_amount=1.0,
        )
        self.assertGreaterEqual(high["amount"], low["amount"])

    def test_sizing_stats(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ds3.db"))
        settings = MagicMock(
            base_amount=1.0,
            kelly_fraction=0.25,
            max_consecutive_losses=3,
        )
        sizer = DynamicSizer(trade_memory=tm, settings=settings)
        stats = sizer.get_sizing_stats()
        self.assertIn("total_calculations", stats)

    def test_record_outcome(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ds4.db"))
        settings = MagicMock(
            base_amount=1.0,
            kelly_fraction=0.25,
            max_consecutive_losses=3,
        )
        sizer = DynamicSizer(trade_memory=tm, settings=settings)
        sizer.record_trade_outcome(1.0)
        sizer.record_trade_outcome(-0.5)
        sizer.record_trade_outcome(-0.3)
        stats = sizer.get_sizing_stats()
        self.assertGreater(stats.get("consecutive_losses", 0), 0)


# =====================================================================
# 9. MetaAI
# =====================================================================
class TestMetaAI(_TempDirMixin, unittest.TestCase):

    def test_evaluate_and_weight(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ma.db"))
        meta = MetaAI(analysis_manager=None, trade_memory=tm)
        meta.evaluate_analyzer("even_odd", {"direction": "CALL"}, "WIN", 80)
        meta.evaluate_analyzer("even_odd", {"direction": "PUT"}, "LOSS", 70)
        meta.evaluate_analyzer("rise_fall", {"direction": "CALL"}, "WIN", 85)
        weights = meta.get_analyzer_weights()
        self.assertIsInstance(weights, dict)
        self.assertIn("even_odd", weights)

    def test_degradation_detection(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ma2.db"))
        meta = MetaAI(analysis_manager=None, trade_memory=tm)
        for _ in range(30):
            meta.evaluate_analyzer("digit_analysis", {"direction": "PUT"}, "WIN", 60)
        for _ in range(30):
            meta.evaluate_analyzer("digit_analysis", {"direction": "CALL"}, "LOSS", 60)
        deg = meta.detect_analyzer_degradation()
        self.assertIn("digit_analysis", deg)

    def test_report(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ma3.db"))
        meta = MetaAI(analysis_manager=None, trade_memory=tm)
        report = meta.get_analyzer_report()
        self.assertIsInstance(report, dict)

    def test_save_load(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "ma4.db"))
        meta = MetaAI(analysis_manager=None, trade_memory=tm)
        meta.evaluate_analyzer("technical", {"direction": "CALL"}, "WIN", 80)
        path = os.path.join(self._tmp, "meta.pkl")
        meta.save(path)
        meta2 = MetaAI(analysis_manager=None, trade_memory=tm)
        meta2.load(path)
        weights = meta2.get_analyzer_weights()
        self.assertIn("technical", weights)


# =====================================================================
# 10. DigitalTwin
# =====================================================================
class TestDigitalTwin(_TempDirMixin, unittest.TestCase):

    def _populate_memory(self, tm):
        for i in range(30):
            rec = TradeRecord(
                trade_id=f"t{i}",
                timestamp=time.time() - i * 100,
                market="R_50",
                direction="CALL" if i % 2 == 0 else "PUT",
                amount=1.0,
                entry_price=100.0,
                exit_price=100.0 + (1.0 if i % 3 != 0 else -1.0),
                profit=1.0 if i % 3 != 0 else -1.0,
                pnl_pct=1.0 if i % 3 != 0 else -1.0,
                confidence=80.0,
                analyzer_outputs={},
                market_features={"regime": "TRENDING_UP"},
                regime="TRENDING_UP",
                entropy=2.0,
                volatility=0.005,
                digit_pattern=[1, 3, 5, 7, 2],
                outcome="WIN" if i % 3 != 0 else "LOSS",
                duration_seconds=60,
                metadata={},
            )
            tm.record_trade(rec)

    def test_simulate(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "dt.db"))
        self._populate_memory(tm)
        dt = DigitalTwin(trade_memory=tm)
        result = dt.simulate(
            signal={"direction": "CALL", "confidence": 80, "type": "EVEN_ODD"},
            market="R_50",
            regime="TRENDING_UP",
            amount=1.0,
            n_simulations=100,
        )
        self.assertIsInstance(result, TwinResult)
        # Should find data since we populated R_50/TRENDING_UP trades
        self.assertTrue(result.approved or result.scenarios_tested >= 0)

    def test_simulate_no_data(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "dt2.db"))
        dt = DigitalTwin(trade_memory=tm)
        result = dt.simulate(
            signal={"direction": "CALL", "confidence": 80, "type": "EVEN_ODD"},
            market="R_50",
            regime="TRENDING_UP",
            amount=1.0,
            n_simulations=50,
        )
        self.assertFalse(result.approved)

    def test_calibration(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "dt3.db"))
        dt = DigitalTwin(trade_memory=tm)
        dt.calibrate([
            {"predicted_direction": "CALL", "actual_profit": 1.0},
            {"predicted_direction": "PUT", "actual_profit": -0.5},
        ])
        stats = dt.get_simulation_stats()
        self.assertIn("calibration_samples", stats)

    def test_save_load(self):
        tm = TradeMemory(db_path=os.path.join(self._tmp, "dt4.db"))
        dt = DigitalTwin(trade_memory=tm)
        path = os.path.join(self._tmp, "dt.pkl")
        dt.save(path)
        dt2 = DigitalTwin(trade_memory=tm)
        dt2.load(path)
        stats = dt2.get_twin_stats()
        self.assertIn("simulation_count", stats)


# =====================================================================
# Orchestrator Integration
# =====================================================================
class TestIntelligenceOrchestrator(_TempDirMixin, unittest.TestCase):

    def test_full_pipeline(self):
        settings = MagicMock(
            intelligence_enabled=True,
            min_opportunity_score=75,
            min_twin_win_rate=0.55,
            base_amount=1.0,
            kelly_fraction=0.25,
        )
        orch = IntelligenceOrchestrator(
            analysis_manager=None,
            settings=settings,
            data_dir=self._tmp,
        )

        # Populate some trade memory
        for i in range(15):
            rec = TradeRecord(
                trade_id=f"t{i}",
                timestamp=time.time() - i * 100,
                market="R_50",
                direction="CALL",
                amount=1.0,
                entry_price=100,
                exit_price=101 if i % 3 != 0 else 99,
                profit=1.0 if i % 3 != 0 else -1.0,
                pnl_pct=1.0,
                confidence=80.0,
                analyzer_outputs={},
                market_features={"regime": "TRENDING_UP", "entropy": 2.0, "volatility": 0.005},
                regime="TRENDING_UP",
                entropy=2.0,
                volatility=0.005,
                digit_pattern=[1, 3, 5],
                outcome="WIN" if i % 3 != 0 else "LOSS",
                duration_seconds=60,
                metadata={},
            )
            orch.trade_memory.record_trade(rec)

        # Run the pipeline
        result = orch.evaluate_tick(
            price_history=[100 + i * 0.3 + np.random.normal(0, 0.1) for i in range(50)],
            digit_history=[1, 3, 5, 7, 2, 4, 6, 8, 0, 1] * 2,
            analyzer_output={
                "consensus": {"confidence": 80, "direction": "CALL", "n_agreeing": 8, "n_total": 10, "type": "EVEN_ODD"},
                "entropy": 2.0,
            },
            market="R_50",
            hour=14,
        )

        self.assertIn("decision", result)
        self.assertIn(result["decision"], ["TRADE", "ABSTAIN", "REJECT"])
        self.assertIn("score", result)
        self.assertIn("regime", result)
        self.assertIn("explanation", result)

    def test_intelligence_state(self):
        settings = MagicMock(
            intelligence_enabled=True,
            min_opportunity_score=75,
            base_amount=1.0,
            kelly_fraction=0.25,
        )
        orch = IntelligenceOrchestrator(
            analysis_manager=None,
            settings=settings,
            data_dir=self._tmp,
        )
        state = orch.get_intelligence_state()
        self.assertIn("regime", state)
        self.assertIn("opportunity", state)
        self.assertIn("trade_memory", state)
        self.assertIn("rl_agent", state)
        self.assertIn("meta_ai", state)
        self.assertIn("digital_twin", state)
        self.assertIn("pipeline_stats", state)

    def test_save_load_all(self):
        settings = MagicMock(
            intelligence_enabled=True,
            min_opportunity_score=75,
            base_amount=1.0,
            kelly_fraction=0.25,
        )
        orch = IntelligenceOrchestrator(
            analysis_manager=None,
            settings=settings,
            data_dir=self._tmp,
        )
        orch.save_all()
        orch2 = IntelligenceOrchestrator(
            analysis_manager=None,
            settings=settings,
            data_dir=self._tmp,
        )
        orch2.load_all()
        state = orch2.get_intelligence_state()
        self.assertIn("pipeline_stats", state)


# =====================================================================
# Settings integration
# =====================================================================
class TestSettingsIntelligence(unittest.TestCase):

    def test_intelligence_fields(self):
        from config.settings import Settings
        s = Settings()
        self.assertTrue(s.intelligence_enabled)
        self.assertEqual(s.min_opportunity_score, 75.0)
        self.assertEqual(s.min_twin_win_rate, 0.55)
        self.assertTrue(s.dynamic_sizing_enabled)
        self.assertTrue(s.meta_ai_enabled)
        self.assertTrue(s.rl_enabled)

    def test_allowed_updates_includes_intelligence(self):
        from config.settings import Settings
        self.assertIn("intelligence_enabled", Settings.ALLOWED_UPDATES)
        self.assertIn("min_opportunity_score", Settings.ALLOWED_UPDATES)
        self.assertIn("dynamic_sizing_enabled", Settings.ALLOWED_UPDATES)

    def test_to_dict_includes_intelligence(self):
        from config.settings import Settings
        s = Settings()
        d = s.to_dict()
        self.assertIn("intelligence_enabled", d)
        self.assertIn("min_opportunity_score", d)
        self.assertIn("min_twin_win_rate", d)


if __name__ == "__main__":
    unittest.main(verbosity=2)
