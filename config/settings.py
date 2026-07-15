import os
from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class Settings:
    """Trading system settings — v3.0 with ensemble ML and regime-aware options."""

    # ── Core trading ──────────────────────────────────────────────────────
    base_amount: float = 1.0
    auto_trading: bool = False
    max_trades_per_hour: int = 10
    min_confidence: int = 70
    stop_loss: float = 50.0
    take_profit: float = 100.0
    max_consecutive_losses: int = 3

    # ── Analyzer toggles ─────────────────────────────────────────────────
    enable_even_odd: bool = True
    enable_rise_fall: bool = True
    enable_over_under: bool = True
    enable_match_diff: bool = True
    enable_digit_analysis: bool = True
    enable_technical: bool = True
    enable_ml: bool = True
    enable_pattern_recognizer: bool = True
    enable_multitimeframe: bool = True
    enable_volatility: bool = True

    # ── Ensemble ML ───────────────────────────────────────────────────────
    use_ensemble: bool = True
    ensemble_voting: str = "soft"            # "soft" or "hard"
    ml_min_confidence: float = 60.0          # min ML confidence to include in signal

    # ── Pattern / entropy filter ──────────────────────────────────────────
    entropy_filter_enabled: bool = True
    min_entropy_threshold: float = 2.2       # skip trades in near-random markets
    chi_threshold: float = 7.0              # chi-sq stat to flag digit skew

    # ── Sniper / streak ───────────────────────────────────────────────────
    min_streak_for_signal: int = 6           # min even/odd streak before reversal signal

    # ── Regime-aware weights ─────────────────────────────────────────────
    regime_aware_weights: bool = True        # let AdaptiveStrategyManager tune weights

    # ── Time filter ───────────────────────────────────────────────────────
    time_filter_enabled: bool = False
    allowed_hours: List[int] = field(default_factory=lambda: list(range(6, 22)))  # 06:00-22:00 UTC

    # ── Position sizing ───────────────────────────────────────────────────
    volatility_sizing: bool = True           # scale stake by inverse-volatility
    kelly_fraction: float = 0.25            # fraction of Kelly criterion to use

    # ── Risk / zero-loss ─────────────────────────────────────────────────
    daily_loss_limit_pct: float = 5.0
    max_drawdown_pct: float = 10.0
    blacklist_expiry_minutes: int = 60       # time-based expiry for blacklisted markets

    # ── Foreign bot (optional external signal provider) ───────────────────
    enable_foreign_bot: bool = False
    foreign_bot_endpoint: str = ""
    foreign_bot_api_key: str = ""

    # ── Intelligence layer ─────────────────────────────────────────────
    intelligence_enabled: bool = True
    min_opportunity_score: float = 75.0     # min composite score to consider trade
    min_twin_win_rate: float = 0.55         # Digital Twin approval threshold
    twin_simulations: int = 500             # scenarios per signal
    nightly_retrain_enabled: bool = True
    retrain_hour: int = 3                   # UTC hour for nightly retrain
    explain_every_tick: bool = False        # only explain when evaluating trades
    dynamic_sizing_enabled: bool = True
    meta_ai_enabled: bool = True
    rl_enabled: bool = True
    case_reasoning_enabled: bool = True

    # ── Research Intelligence Layer (advanced 12) ──────────────────────
    research_mode_enabled: bool = True
    market_dna_enabled: bool = True
    similarity_search_enabled: bool = True
    bayesian_engine_enabled: bool = True
    ensemble_intelligence_enabled: bool = True
    online_learner_enabled: bool = True
    abstention_model_enabled: bool = True
    meta_supervisor_enabled: bool = True
    explainable_engine_enabled: bool = True
    backtesting_enabled: bool = True
    capital_preservation_enabled: bool = True
    self_improvement_enabled: bool = True
    min_bayesian_confidence: float = 0.55
    max_abstention_probability: float = 0.6
    walk_forward_train_days: int = 30
    walk_forward_test_days: int = 7
    monte_carlo_simulations: int = 1000
    auto_rollback_threshold: float = 0.05

    # ── Notifications ────────────────────────────────────────────────────
    telegram_alerts: bool = False

    # ── Whitelist of fields allowed via API update ───────────────────────
    ALLOWED_UPDATES = {
        "base_amount", "auto_trading", "max_trades_per_hour", "min_confidence",
        "stop_loss", "take_profit", "max_consecutive_losses",
        "enable_even_odd", "enable_rise_fall", "enable_over_under",
        "enable_match_diff", "enable_digit_analysis", "enable_technical",
        "enable_ml", "enable_pattern_recognizer", "enable_multitimeframe",
        "enable_volatility", "use_ensemble", "ensemble_voting",
        "ml_min_confidence", "entropy_filter_enabled", "min_entropy_threshold",
        "chi_threshold", "min_streak_for_signal", "regime_aware_weights",
        "time_filter_enabled", "allowed_hours", "volatility_sizing",
        "kelly_fraction", "daily_loss_limit_pct", "max_drawdown_pct",
        "blacklist_expiry_minutes", "enable_foreign_bot", "telegram_alerts",
        "intelligence_enabled", "min_opportunity_score", "min_twin_win_rate",
        "twin_simulations", "dynamic_sizing_enabled", "meta_ai_enabled",
        "rl_enabled", "case_reasoning_enabled",
        "research_mode_enabled", "market_dna_enabled", "similarity_search_enabled",
        "bayesian_engine_enabled", "ensemble_intelligence_enabled", "online_learner_enabled",
        "abstention_model_enabled", "meta_supervisor_enabled", "explainable_engine_enabled",
        "backtesting_enabled", "capital_preservation_enabled", "self_improvement_enabled",
    }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_amount": self.base_amount,
            "auto_trading": self.auto_trading,
            "max_trades_per_hour": self.max_trades_per_hour,
            "min_confidence": self.min_confidence,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "max_consecutive_losses": self.max_consecutive_losses,
            "enable_even_odd": self.enable_even_odd,
            "enable_rise_fall": self.enable_rise_fall,
            "enable_over_under": self.enable_over_under,
            "enable_match_diff": self.enable_match_diff,
            "enable_digit_analysis": self.enable_digit_analysis,
            "enable_technical": self.enable_technical,
            "enable_ml": self.enable_ml,
            "enable_pattern_recognizer": self.enable_pattern_recognizer,
            "use_ensemble": self.use_ensemble,
            "ensemble_voting": self.ensemble_voting,
            "ml_min_confidence": self.ml_min_confidence,
            "entropy_filter_enabled": self.entropy_filter_enabled,
            "min_entropy_threshold": self.min_entropy_threshold,
            "chi_threshold": self.chi_threshold,
            "min_streak_for_signal": self.min_streak_for_signal,
            "regime_aware_weights": self.regime_aware_weights,
            "time_filter_enabled": self.time_filter_enabled,
            "allowed_hours": self.allowed_hours,
            "volatility_sizing": self.volatility_sizing,
            "kelly_fraction": self.kelly_fraction,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "blacklist_expiry_minutes": self.blacklist_expiry_minutes,
            "enable_foreign_bot": self.enable_foreign_bot,
            "foreign_bot_endpoint": self.foreign_bot_endpoint,
            "foreign_bot_api_key": self.foreign_bot_api_key,
            "telegram_alerts": self.telegram_alerts,
            "intelligence_enabled": self.intelligence_enabled,
            "min_opportunity_score": self.min_opportunity_score,
            "min_twin_win_rate": self.min_twin_win_rate,
            "twin_simulations": self.twin_simulations,
            "dynamic_sizing_enabled": self.dynamic_sizing_enabled,
            "meta_ai_enabled": self.meta_ai_enabled,
            "rl_enabled": self.rl_enabled,
            "case_reasoning_enabled": self.case_reasoning_enabled,
            "research_mode_enabled": self.research_mode_enabled,
            "market_dna_enabled": self.market_dna_enabled,
            "similarity_search_enabled": self.similarity_search_enabled,
            "bayesian_engine_enabled": self.bayesian_engine_enabled,
            "ensemble_intelligence_enabled": self.ensemble_intelligence_enabled,
            "online_learner_enabled": self.online_learner_enabled,
            "abstention_model_enabled": self.abstention_model_enabled,
            "meta_supervisor_enabled": self.meta_supervisor_enabled,
            "explainable_engine_enabled": self.explainable_engine_enabled,
            "backtesting_enabled": self.backtesting_enabled,
            "capital_preservation_enabled": self.capital_preservation_enabled,
            "self_improvement_enabled": self.self_improvement_enabled,
        }

    def update(self, data: Dict[str, Any]):
        """Update settings from dictionary (whitelist-only to prevent injection)"""
        for key, value in data.items():
            if key in self.ALLOWED_UPDATES and hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables where available."""
        s = cls()
        s.base_amount = float(os.getenv("BASE_AMOUNT", s.base_amount))
        s.min_confidence = int(os.getenv("MIN_CONFIDENCE", s.min_confidence))
        s.stop_loss = float(os.getenv("STOP_LOSS", s.stop_loss))
        s.take_profit = float(os.getenv("TAKE_PROFIT", s.take_profit))
        s.max_consecutive_losses = int(os.getenv("MAX_CONSECUTIVE_LOSSES", s.max_consecutive_losses))
        s.daily_loss_limit_pct = float(os.getenv("DAILY_LOSS_LIMIT_PERCENT", s.daily_loss_limit_pct))
        s.chi_threshold = float(os.getenv("CHI_THRESHOLD", s.chi_threshold))
        s.min_streak_for_signal = int(os.getenv("MIN_STREAK", s.min_streak_for_signal))
        return s
