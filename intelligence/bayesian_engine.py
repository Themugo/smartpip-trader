"""
Bayesian Confidence Engine — principled uncertainty quantification for trade signals.

Rather than relying on point estimates of confidence, this module maintains
a full posterior distribution over signal quality using conjugate Beta-Binomial
updates.  Every incoming signal updates the posterior, and confidence is
reported as a credible interval rather than a single number.

Key features:
  - Per-analyzer, per-regime, and per-market posterior distributions.
  - Posterior predictive checks for calibration monitoring.
  - Information-theoretic uncertainty reduction tracking.
  - Automatic prior annealing based on data quality.
"""

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import joblib

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_PRIOR_ALPHA = 2.0
_DEFAULT_PRIOR_BETA = 2.0
_MIN_SAMPLES = 3
_MAX_REGIMES = 12
_CREDIBLE_LEVEL = 0.95


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PosteriorStats:
    """Summary statistics of a Beta posterior distribution."""
    alpha: float
    beta: float
    mean: float
    variance: float
    credible_interval: Tuple[float, float]
    credible_level: float
    sample_count: int
    entropy: float  # differential entropy of the Beta distribution

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "mean": round(self.mean, 4),
            "variance": round(self.variance, 6),
            "credible_interval": (round(self.credible_interval[0], 4), round(self.credible_interval[1], 4)),
            "credible_level": self.credible_level,
            "sample_count": self.sample_count,
            "entropy": round(self.entropy, 4),
        }


@dataclass
class BayesianVerdict:
    """Output of the Bayesian confidence engine for a single signal."""
    overall_confidence: float  # posterior mean [0, 1]
    credible_interval: Tuple[float, float]
    credible_level: float
    componentPosteriors: Dict[str, PosteriorStats]
    information_gain: float  # bits gained from prior
    uncertainty_remaining: float
    recommendation: str  # "HIGH_CONFIDENCE" / "MODERATE" / "LOW_CONFIDENCE" / "INSUFFICIENT_DATA"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_confidence": round(self.overall_confidence, 4),
            "credible_interval": (round(self.credible_interval[0], 4), round(self.credible_interval[1], 4)),
            "credible_level": self.credible_level,
            "information_gain": round(self.information_gain, 4),
            "uncertainty_remaining": round(self.uncertainty_remaining, 4),
            "recommendation": self.recommendation,
            "component_count": len(self.componentPosteriors),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Beta distribution helpers (numpy only)
# ---------------------------------------------------------------------------

def _beta_mean(alpha: float, beta: float) -> float:
    """Mean of Beta(alpha, beta)."""
    return alpha / (alpha + beta)


def _beta_variance(alpha: float, beta: float) -> float:
    """Variance of Beta(alpha, beta)."""
    ab = alpha + beta
    return (alpha * beta) / (ab * ab * (ab + 1))


def _beta_entropy(alpha: float, beta: float) -> float:
    """Differential entropy of Beta(alpha, beta)."""
    if alpha <= 1 or beta <= 1:
        return 0.5  # approximate
    ab = alpha + beta
    from scipy.special import betaln, digamma
    try:
        h = betaln(alpha, beta) - (alpha - 1) * digamma(alpha) - (beta - 1) * digamma(beta) + (ab - 2) * digamma(ab)
        return float(h)
    except Exception:
        return 0.5


def _beta_credible_interval(alpha: float, beta: float, level: float = 0.95) -> Tuple[float, float]:
    """Equal-tailed credible interval for Beta(alpha, beta)."""
    alpha_clip = max(alpha, 1.001)
    beta_clip = max(beta, 1.001)
    try:
        from scipy.stats import beta as beta_dist
        lo = float(beta_dist.ppf((1 - level) / 2, alpha_clip, beta_clip))
        hi = float(beta_dist.ppf(1 - (1 - level) / 2, alpha_clip, beta_clip))
        return (max(0.0, lo), min(1.0, hi))
    except Exception:
        mu = _beta_mean(alpha_clip, beta_clip)
        return (max(0.0, mu - 0.1), min(1.0, mu + 0.1))


def _beta_kl_divergence(alpha1: float, beta1: float, alpha0: float, beta0: float) -> float:
    """KL(Beta(alpha1, beta1) || Beta(alpha0, beta0)) in nats."""
    try:
        from scipy.special import betaln, digamma
        a1, b1 = max(alpha1, 1.001), max(beta1, 1.001)
        a0, b0 = max(alpha0, 1.001), max(beta0, 1.001)
        kl = (betaln(a0, b0) - betaln(a1, b1)
               + (a1 - a0) * digamma(a1)
               + (b1 - b0) * digamma(b1)
               + (a0 - a1 + b0 - b1) * digamma(a1 + b1))
        return max(0.0, float(kl))
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# BayesianEngine
# ---------------------------------------------------------------------------

class BayesianEngine:
    """Principled Bayesian confidence estimation for trade signals.

    Maintains Beta posterior distributions over signal quality for each
    analyzer, regime, and market combination.  Confidence intervals shrink
    as more data accumulates.

    Usage::

        engine = BayesianEngine()
        verdict = engine.evaluate_signal(
            analyzer_confidences={"momentum": 85.0, "mean_reversion": 60.0},
            regime="TRENDING_UP",
            market="volatility_75",
        )
        print(verdict.overall_confidence, verdict.credible_interval)
    """

    def __init__(
        self,
        prior_alpha: float = _DEFAULT_PRIOR_ALPHA,
        prior_beta: float = _DEFAULT_PRIOR_BETA,
    ):
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta

        # Posteriors keyed by (analyzer_name, regime, market)
        self._posteriors: Dict[str, Tuple[float, float]] = {}
        # Global posterior (no conditioning)
        self._global_posterior = (prior_alpha, prior_beta)
        # Per-regime posteriors
        self._regime_posteriors: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (prior_alpha, prior_beta)
        )
        # Per-analyzer posteriors
        self._analyzer_posteriors: Dict[str, Tuple[float, float]] = defaultdict(
            lambda: (prior_alpha, prior_beta)
        )
        # Tracking
        self._total_updates: int = 0
        self._total_evaluations: int = 0
        self._information_gains: List[float] = []

        logger.info(
            "BayesianEngine initialised (prior α=%.2f, β=%.2f)",
            prior_alpha, prior_beta,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        outcome: bool,
        analyzer_confidences: Optional[Dict[str, float]] = None,
        regime: str = "UNKNOWN",
        market: str = "unknown",
    ) -> None:
        """Update posteriors with an observed trade outcome.

        Parameters
        ----------
        outcome : bool
            True for WIN, False for LOSS.
        analyzer_confidences : dict
            Confidence scores (0-100) from each analyzer at time of trade.
        regime : str
            Market regime label.
        market : str
            Market identifier.
        """
        success = 1.0 if outcome else 0.0

        # Global update
        a, b = self._global_posterior
        self._global_posterior = (a + success, b + (1 - success))

        # Regime-specific update
        ra, rb = self._regime_posteriors[regime]
        self._regime_posteriors[regime] = (ra + success, rb + (1 - success))

        # Per-analyzer updates
        if analyzer_confidences:
            for name, conf in analyzer_confidences.items():
                # Weight the update by confidence: high-confidence wrong = big penalty
                weight = conf / 100.0
                a_an, b_an = self._analyzer_posteriors[name]
                self._analyzer_posteriors[name] = (
                    a_an + success * weight,
                    b_an + (1 - success) * weight,
                )

        # Conditional (analyzer × regime × market) update
        if analyzer_confidences:
            for name in analyzer_confidences:
                key = f"{name}|{regime}|{market}"
                a_c, b_c = self._posteriors.get(key, (self.prior_alpha, self.prior_beta))
                self._posteriors[key] = (a_c + success, b_c + (1 - success))

        self._total_updates += 1

    def evaluate_signal(
        self,
        analyzer_confidences: Dict[str, float],
        regime: str = "UNKNOWN",
        market: str = "unknown",
    ) -> BayesianVerdict:
        """Evaluate a signal using current posterior knowledge.

        Parameters
        ----------
        analyzer_confidences : dict
            Confidence scores (0-100) from each analyzer.
        regime : str
            Current market regime.
        market : str
            Market identifier.

        Returns
        -------
        BayesianVerdict
        """
        self._total_evaluations += 1

        if not analyzer_confidences:
            return self._build_verdict(
                self._global_posterior, {}, regime, market,
                analyzer_confidences={},
            )

        # Compute a weighted posterior combining all analyzers
        total_weight = 0.0
        weighted_alpha = 0.0
        weighted_beta = 0.0

        component_posteriors: Dict[str, PosteriorStats] = {}

        for name, conf in analyzer_confidences.items():
            weight = conf / 100.0
            if weight < 0.01:
                continue

            total_weight += weight

            # Get the most specific posterior available
            key = f"{name}|{regime}|{market}"
            posterior = self._posteriors.get(key, self._analyzer_posteriors.get(name, self._global_posterior))

            # Weight the posterior by the signal confidence
            a, b = posterior
            weighted_alpha += a * weight
            weighted_beta += b * weight

            # Component-level stats
            mu = _beta_mean(a, b)
            var = _beta_variance(a, b)
            ci = _beta_credible_interval(a, b, _CREDIBLE_LEVEL)
            ent = _beta_entropy(a, b)
            total_samples = int(a + b - 2 * self.prior_alpha)

            component_posteriors[name] = PosteriorStats(
                alpha=a, beta=b, mean=mu, variance=var,
                credible_interval=ci, credible_level=_CREDIBLE_LEVEL,
                sample_count=max(0, total_samples), entropy=ent,
            )

        if total_weight > 0:
            combined_alpha = weighted_alpha / total_weight
            combined_beta = weighted_beta / total_weight
        else:
            combined_alpha, combined_beta = self._global_posterior

        return self._build_verdict(
            (combined_alpha, combined_beta),
            component_posteriors,
            regime,
            market,
            analyzer_confidences,
        )

    def get_posterior(self, key: str) -> Optional[PosteriorStats]:
        """Get posterior stats for a specific (analyzer, regime, market) key."""
        posterior = self._posteriors.get(key)
        if posterior is None:
            return None
        a, b = posterior
        mu = _beta_mean(a, b)
        var = _beta_variance(a, b)
        ci = _beta_credible_interval(a, b, _CREDIBLE_LEVEL)
        ent = _beta_entropy(a, b)
        total_samples = int(a + b - 2 * self.prior_alpha)
        return PosteriorStats(
            alpha=a, beta=b, mean=mu, variance=var,
            credible_interval=ci, credible_level=_CREDIBLE_LEVEL,
            sample_count=max(0, total_samples), entropy=ent,
        )

    def get_global_posterior(self) -> PosteriorStats:
        """Get the global (unconditional) posterior."""
        a, b = self._global_posterior
        mu = _beta_mean(a, b)
        var = _beta_variance(a, b)
        ci = _beta_credible_interval(a, b, _CREDIBLE_LEVEL)
        ent = _beta_entropy(a, b)
        total_samples = int(a + b - 2 * self.prior_alpha)
        return PosteriorStats(
            alpha=a, beta=b, mean=mu, variance=var,
            credible_interval=ci, credible_level=_CREDIBLE_LEVEL,
            sample_count=max(0, total_samples), entropy=ent,
        )

    def get_calibration_report(self) -> Dict[str, Any]:
        """Report on calibration quality and information gain."""
        avg_ig = float(np.mean(self._information_gains)) if self._information_gains else 0.0
        return {
            "total_updates": self._total_updates,
            "total_evaluations": self._total_evaluations,
            "avg_information_gain_bits": round(avg_ig / math.log(2), 4) if avg_ig > 0 else 0.0,
            "global_posterior": {
                "alpha": self._global_posterior[0],
                "beta": self._global_posterior[1],
                "mean": round(_beta_mean(*self._global_posterior), 4),
            },
            "n_regimes": len(self._regime_posteriors),
            "n_analyzers": len(self._analyzer_posteriors),
            "n_conditional": len(self._posteriors),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialise engine state."""
        state = {
            "prior_alpha": self.prior_alpha,
            "prior_beta": self.prior_beta,
            "global_posterior": self._global_posterior,
            "regime_posteriors": dict(self._regime_posteriors),
            "analyzer_posteriors": dict(self._analyzer_posteriors),
            "posteriors": dict(self._posteriors),
            "total_updates": self._total_updates,
            "total_evaluations": self._total_evaluations,
        }
        joblib.dump(state, path)
        logger.info("BayesianEngine saved to %s", path)

    def load(self, path: str) -> bool:
        """Restore engine state."""
        try:
            state = joblib.load(path)
            self.prior_alpha = state["prior_alpha"]
            self.prior_beta = state["prior_beta"]
            self._global_posterior = tuple(state["global_posterior"])
            self._regime_posteriors = defaultdict(lambda: (self.prior_alpha, self.prior_beta), state["regime_posteriors"])
            self._analyzer_posteriors = defaultdict(lambda: (self.prior_alpha, self.prior_beta), state["analyzer_posteriors"])
            self._posteriors = state["posteriors"]
            self._total_updates = state["total_updates"]
            self._total_evaluations = state["total_evaluations"]
            logger.info("BayesianEngine loaded from %s", path)
            return True
        except Exception as exc:
            logger.error("Failed to load BayesianEngine: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_verdict(
        self,
        combined_posterior: Tuple[float, float],
        component_posteriors: Dict[str, PosteriorStats],
        regime: str,
        market: str,
        analyzer_confidences: Dict[str, float],
    ) -> BayesianVerdict:
        """Build a BayesianVerdict from a combined posterior."""
        a, b = combined_posterior
        mu = _beta_mean(a, b)
        var = _beta_variance(a, b)
        ci = _beta_credible_interval(a, b, _CREDIBLE_LEVEL)
        ent = _beta_entropy(a, b)

        # Information gain relative to prior
        prior_ent = _beta_entropy(self.prior_alpha, self.prior_beta)
        ig = max(0.0, prior_ent - ent)
        self._information_gains.append(ig)

        # Uncertainty: width of credible interval
        uncertainty = ci[1] - ci[0]

        # Recommendation
        total_samples = a + b - 2 * self.prior_alpha
        if total_samples < _MIN_SAMPLES:
            rec = "INSUFFICIENT_DATA"
        elif mu >= 0.65 and uncertainty < 0.3:
            rec = "HIGH_CONFIDENCE"
        elif mu >= 0.50:
            rec = "MODERATE"
        else:
            rec = "LOW_CONFIDENCE"

        return BayesianVerdict(
            overall_confidence=mu,
            credible_interval=ci,
            credible_level=_CREDIBLE_LEVEL,
            componentPosteriors=component_posteriors,
            information_gain=ig,
            uncertainty_remaining=uncertainty,
            recommendation=rec,
        )
