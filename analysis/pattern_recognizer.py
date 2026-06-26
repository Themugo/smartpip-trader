"""
Pattern Recognizer: advanced statistical analysis of digit sequences.
Uses chi-squared test, runs test, Shannon entropy, mean-reversion probability,
and autocorrelation to detect exploitable market patterns.
"""
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from scipy import stats
from collections import Counter
from models import AnalysisResult
from .base_analyzer import BaseAnalyzer


class PatternRecognizer(BaseAnalyzer):
    """
    Detects statistically significant patterns in Deriv digit streams.
    Returns directional signals only when statistical edge exceeds threshold.
    """

    def __init__(self, chi_threshold: float = 7.0, entropy_threshold: float = 2.8):
        super().__init__(min_data_points=20)
        self.chi_threshold = chi_threshold
        self.entropy_threshold = entropy_threshold
        self.last_metrics: Dict[str, Any] = {}

    def analyze(self, data: Dict[str, Any]) -> AnalysisResult:
        should_skip, reason = self.should_skip_analysis(data)
        if should_skip:
            return AnalysisResult(
                model_name="pattern_recognizer",
                prediction=None, confidence=0,
                data={"skipped": True, "reason": reason}
            )

        digits = data.get("last_20_digits", [])
        price_history = data.get("price_history", [])

        if len(digits) < 15:
            return AnalysisResult(
                model_name="pattern_recognizer",
                prediction=None, confidence=0,
                data={"skipped": True, "reason": "Need >= 15 digits"}
            )

        metrics = self._compute_metrics(digits, price_history)
        self.last_metrics = metrics
        prediction, confidence, reason_text = self._generate_signal(metrics)

        return AnalysisResult(
            model_name="pattern_recognizer",
            prediction=prediction,
            confidence=confidence,
            data={**metrics, "signal_reason": reason_text}
        )

    def _compute_metrics(self, digits: List[int], prices: List[float]) -> Dict[str, Any]:
        arr = np.array(digits)

        # 1. Shannon entropy (theoretical max for 10 digits = log2(10) ≈ 3.32)
        counts = np.bincount(arr, minlength=10)
        probs = counts / counts.sum()
        probs_nonzero = probs[probs > 0]
        entropy = float(-np.sum(probs_nonzero * np.log2(probs_nonzero)))

        # 2. Chi-squared test for uniform distribution (expected: 10% each)
        n = len(arr)
        expected = np.full(10, n / 10.0)
        chi2_stat, chi2_p = stats.chisquare(counts, f_exp=expected)

        # 3. Runs test for randomness (too many/few runs = non-random)
        even_odd = [x % 2 for x in arr]
        runs_stat, runs_p = self._runs_test(even_odd)

        # 4. Autocorrelation at lag 1 (serial dependency)
        if len(arr) >= 4:
            ac1 = float(np.corrcoef(arr[:-1], arr[1:])[0, 1]) if len(arr) > 2 else 0.0
        else:
            ac1 = 0.0

        # 5. Even/odd streak
        eo_streak, eo_dir = self._streak_info(even_odd)

        # 6. High/low bias (0-4 vs 5-9)
        low_pct = float(np.sum(arr < 5) / n)
        high_pct = 1.0 - low_pct

        # 7. Hot digit (most over-represented)
        expected_pct = 0.1
        deviations = {d: float((counts[d] / n) - expected_pct) for d in range(10)}
        hot_digit = max(deviations, key=lambda d: abs(deviations[d]))
        hot_dev = deviations[hot_digit]

        # 8. Mean reversion score from prices
        mean_rev_score = 0.0
        if len(prices) >= 10:
            recent = np.array(prices[-10:])
            mean_rev_score = float(abs(recent[-1] - recent.mean()) / (recent.std() + 1e-10))

        return {
            "entropy": round(entropy, 4),
            "entropy_pct": round(entropy / 3.321928 * 100, 1),  # % of theoretical max
            "chi2_stat": round(float(chi2_stat), 3),
            "chi2_p": round(float(chi2_p), 4),
            "runs_stat": round(runs_stat, 3),
            "runs_p": round(float(runs_p), 4),
            "autocorr_lag1": round(ac1, 4),
            "even_odd_streak": eo_streak,
            "streak_direction": eo_dir,
            "low_pct": round(low_pct, 4),
            "high_pct": round(high_pct, 4),
            "hot_digit": hot_digit,
            "hot_deviation": round(hot_dev, 4),
            "digit_counts": counts.tolist(),
            "mean_reversion_score": round(mean_rev_score, 4),
        }

    def _generate_signal(self, m: Dict[str, Any]) -> Tuple[Optional[str], float, str]:
        signals = []
        reasons = []

        # --- Streak exhaustion signal ---
        streak = m["even_odd_streak"]
        if streak >= 6:
            prob_continue = 0.5 ** (streak + 1)
            reversal_conf = (1 - prob_continue) * 100
            if reversal_conf > 65:
                direction = "EVEN" if m["streak_direction"] == "ODD" else "ODD"
                signals.append(("RISE" if direction == "EVEN" else "FALL", reversal_conf * 0.8))
                reasons.append(f"Streak exhaustion {streak} {m['streak_direction']} → reversal ({reversal_conf:.0f}%)")

        # --- Chi-squared skew signal ---
        if m["chi2_stat"] > self.chi_threshold and m["chi2_p"] < 0.1:
            skew_conf = min(90, 50 + (m["chi2_stat"] - self.chi_threshold) * 2)
            hot_dev = m["hot_deviation"]
            # if digits are skewed low, expect reversion high and vice versa
            direction = "RISE" if m["low_pct"] > 0.55 else "FALL" if m["high_pct"] > 0.55 else None
            if direction:
                signals.append((direction, skew_conf))
                reasons.append(f"Chi-sq {m['chi2_stat']:.1f} (p={m['chi2_p']:.3f}) → {direction}")

        # --- Entropy signal (low entropy = patterned market) ---
        if m["entropy"] < self.entropy_threshold:
            low_entropy_conf = min(85, (self.entropy_threshold - m["entropy"]) / self.entropy_threshold * 100 + 50)
            # Low entropy with even skew → mean revert
            if m["low_pct"] > 0.6:
                signals.append(("RISE", low_entropy_conf))
                reasons.append(f"Low entropy {m['entropy']:.2f} + low-digit bias → RISE")
            elif m["high_pct"] > 0.6:
                signals.append(("FALL", low_entropy_conf))
                reasons.append(f"Low entropy {m['entropy']:.2f} + high-digit bias → FALL")

        # --- Mean reversion signal ---
        if m["mean_reversion_score"] > 2.0:
            rev_conf = min(80, 50 + m["mean_reversion_score"] * 5)
            signals.append(("RISE" if m["mean_reversion_score"] > 0 else "FALL", rev_conf))
            reasons.append(f"Mean reversion score {m['mean_reversion_score']:.2f}")

        if not signals:
            return None, 0, "No significant pattern detected"

        # Aggregate: weighted vote
        call_score = sum(c for d, c in signals if d in ("RISE", "CALL"))
        put_score = sum(c for d, c in signals if d in ("FALL", "PUT"))
        if call_score == put_score:
            return None, 0, "Conflicting signals — no trade"
        direction = "CALL" if call_score > put_score else "PUT"
        confidence = max(call_score, put_score) / max(1, len(signals))
        confidence = min(90, confidence)
        return direction, round(confidence, 1), " | ".join(reasons)

    @staticmethod
    def _runs_test(sequence: List[int]) -> Tuple[float, float]:
        """Wald-Wolfowitz runs test for randomness."""
        n = len(sequence)
        if n < 10:
            return 0.0, 1.0
        n1 = sum(sequence)
        n2 = n - n1
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0
        runs = 1
        for i in range(1, n):
            if sequence[i] != sequence[i - 1]:
                runs += 1
        mu = (2 * n1 * n2 / n) + 1
        sigma2 = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n ** 2 * (n - 1))
        if sigma2 <= 0:
            return 0.0, 1.0
        z = (runs - mu) / (sigma2 ** 0.5)
        p_value = float(2 * (1 - stats.norm.cdf(abs(z))))
        return float(z), p_value

    @staticmethod
    def _streak_info(even_odd: List[int]) -> Tuple[int, str]:
        if not even_odd:
            return 0, "NONE"
        current = even_odd[-1]
        streak = 1
        for i in range(len(even_odd) - 2, -1, -1):
            if even_odd[i] == current:
                streak += 1
            else:
                break
        direction = "EVEN" if current == 0 else "ODD"
        return streak, direction

    def get_market_health(self) -> Dict[str, Any]:
        """Return human-readable market health from last analysis."""
        if not self.last_metrics:
            return {"status": "no_data"}
        e = self.last_metrics.get("entropy", 3.32)
        chi = self.last_metrics.get("chi2_stat", 0)
        if e > 3.0 and chi < 5:
            health = "random"
            note = "Market behaving randomly — low edge"
        elif e < 2.5 or chi > 15:
            health = "patterned"
            note = "Strong pattern detected — high edge opportunity"
        else:
            health = "moderate"
            note = "Mild pattern — trade with caution"
        return {
            "status": health,
            "note": note,
            "entropy": self.last_metrics.get("entropy"),
            "entropy_pct": self.last_metrics.get("entropy_pct"),
            "chi2": self.last_metrics.get("chi2_stat"),
        }
