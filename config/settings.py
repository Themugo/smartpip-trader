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

    # ── Notifications ────────────────────────────────────────────────────
    telegram_alerts: bool = False

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
        }

    def update(self, data: Dict[str, Any]):
        for key, value in data.items():
            if hasattr(self, key):
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
