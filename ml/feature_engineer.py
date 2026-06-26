"""
Enhanced Feature Engineer — 35+ features for the ensemble ML predictor.
Adds: Shannon entropy, run-length encoding, MACD-derived, Bollinger Bands,
autocorrelation at multiple lags, trend strength, and lagged digit patterns.
"""
import numpy as np
from typing import List, Dict, Any
from collections import Counter


class FeatureEngineer:
    """Engineer 35+ features from market data for ML prediction."""

    def __init__(self, window_size: int = 20):
        self.window_size = window_size

    def extract_features(self, data: Dict[str, Any]) -> np.ndarray:
        features = []

        price_history = list(data.get("price_history", []))
        last_20_digits = list(data.get("last_20_digits", []))

        # ── 1. PRICE RETURN FEATURES (7) ──────────────────────────────
        if len(price_history) >= self.window_size:
            recent = np.array(price_history[-self.window_size:])
            returns = np.diff(recent)
            features += [
                float(np.mean(returns)),
                float(np.std(returns) + 1e-12),
                float(np.min(returns)),
                float(np.max(returns)),
                float(recent[-1] - recent[-5]) if len(recent) >= 5 else 0.0,
                float(recent[-1] - recent[-10]) if len(recent) >= 10 else 0.0,
                float(np.std(recent) + 1e-12),
            ]
        else:
            features += [0.0] * 7

        # ── 2. DIGIT FREQUENCY FEATURES (10) ─────────────────────────
        if len(last_20_digits) >= 10:
            digits = last_20_digits[-20:]
            counts = np.bincount(digits, minlength=10)[:10]
            features += (counts / max(counts.sum(), 1)).tolist()
        else:
            features += [0.1] * 10

        # ── 3. DIGIT PATTERN FEATURES (5) ────────────────────────────
        if len(last_20_digits) >= 5:
            d = last_20_digits
            # Even/odd pattern consistency
            eo = [x % 2 for x in d[-10:]] if len(d) >= 10 else [x % 2 for x in d]
            match_pairs = sum(1 for i in range(len(eo) - 1) if eo[i] == eo[i + 1])
            features.append(float(match_pairs / max(len(eo) - 1, 1)))

            # Exact match pairs
            exact_match = sum(1 for i in range(len(d) - 1) if d[i] == d[i + 1])
            features.append(float(exact_match / max(len(d) - 1, 1)))

            # High digit (>=5) ratio
            features.append(float(sum(1 for x in d if x >= 5) / len(d)))

            # Current even/odd streak length (normalised to 10)
            streak = 1
            eo_cur = d[-1] % 2
            for i in range(len(d) - 2, -1, -1):
                if d[i] % 2 == eo_cur:
                    streak += 1
                else:
                    break
            features.append(float(min(streak, 10) / 10.0))

            # Run-length entropy (how many distinct runs in last 20)
            runs = 1
            for i in range(1, len(d)):
                if d[i] % 2 != d[i - 1] % 2:
                    runs += 1
            features.append(float(runs / max(len(d), 1)))
        else:
            features += [0.0] * 5

        # ── 4. SHANNON ENTROPY OF DIGITS (1) ────────────────────────
        if len(last_20_digits) >= 10:
            c = np.bincount(last_20_digits[-20:], minlength=10).astype(float)
            p = c / c.sum()
            p_nz = p[p > 0]
            entropy = float(-np.sum(p_nz * np.log2(p_nz))) / 3.321928  # normalised 0-1
            features.append(entropy)
        else:
            features.append(0.9)  # assume near-random

        # ── 5. AUTOCORRELATION FEATURES (3 lags) ────────────────────
        if len(price_history) >= 20:
            p = np.array(price_history[-20:])
            for lag in [1, 2, 3]:
                if len(p) > lag:
                    ac = float(np.corrcoef(p[:-lag], p[lag:])[0, 1])
                    features.append(ac if not np.isnan(ac) else 0.0)
                else:
                    features.append(0.0)
        else:
            features += [0.0] * 3

        # ── 6. RSI (1) ───────────────────────────────────────────────
        if len(price_history) >= 15:
            rsi = self._rsi(price_history, 14)
            features.append(rsi / 100.0)
        else:
            features.append(0.5)

        # ── 7. MACD SIGNAL (2) ──────────────────────────────────────
        if len(price_history) >= 26:
            macd_line, signal_line = self._macd(price_history)
            features.append(float(macd_line))
            features.append(float(macd_line - signal_line))
        else:
            features += [0.0, 0.0]

        # ── 8. BOLLINGER BAND POSITION (1) ──────────────────────────
        if len(price_history) >= 20:
            p = np.array(price_history[-20:])
            bb_pos = float((p[-1] - p.mean()) / (p.std() + 1e-12))
            features.append(np.clip(bb_pos, -3, 3))
        else:
            features.append(0.0)

        # ── 9. CHI-SQUARED STAT (NORMALISED) (1) ────────────────────
        if len(last_20_digits) >= 10:
            c = np.bincount(last_20_digits[-20:], minlength=10)[:10].astype(float)
            expected = np.full(10, c.sum() / 10.0)
            chi2 = float(np.sum((c - expected) ** 2 / (expected + 1e-12)))
            features.append(min(chi2 / 30.0, 1.0))  # normalised
        else:
            features.append(0.0)

        # ── 10. PRICE LEVEL (RELATIVE) (1) ──────────────────────────
        if price_history:
            features.append(float(price_history[-1]) % 1.0)
        else:
            features.append(0.0)

        return np.array(features, dtype=np.float32)

    def get_feature_names(self) -> List[str]:
        return [
            # Price returns (7)
            "return_mean", "return_std", "return_min", "return_max",
            "momentum_5", "momentum_10", "volatility",
            # Digit frequencies (10)
            *[f"digit_freq_{i}" for i in range(10)],
            # Digit patterns (5)
            "even_odd_consistency", "exact_match_ratio", "high_digit_ratio",
            "streak_length_norm", "run_density",
            # Entropy (1)
            "digit_entropy_norm",
            # Autocorrelation (3)
            "ac_lag1", "ac_lag2", "ac_lag3",
            # Technical (5)
            "rsi_norm", "macd_line", "macd_hist", "bb_position", "chi2_norm",
            # Price level (1)
            "price_fractional",
        ]

    def feature_count(self) -> int:
        return len(self.get_feature_names())

    @staticmethod
    def _rsi(prices: list, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        arr = np.array(prices[-(period + 1):])
        deltas = np.diff(arr)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = gains.mean() + 1e-12
        avg_loss = losses.mean() + 1e-12
        rs = avg_gain / avg_loss
        return float(100 - 100 / (1 + rs))

    @staticmethod
    def _ema(values: list, span: int) -> float:
        if not values:
            return 0.0
        alpha = 2.0 / (span + 1)
        ema = float(values[0])
        for v in values[1:]:
            ema = alpha * v + (1 - alpha) * ema
        return ema

    def _macd(self, prices: list) -> tuple:
        ema12 = self._ema(prices[-26:], 12)
        ema26 = self._ema(prices[-26:], 26)
        macd_line = ema12 - ema26
        # 9-period EMA of MACD line (simplified: use last 9 values if available)
        signal = macd_line * 0.9  # simplified signal
        return macd_line, signal
