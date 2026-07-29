from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


@dataclass
class QGapConfig:
    tau_min: float = 0.02
    tau_max: float = 10.0
    deterministic_gap: float = 0.20
    random_gap: float = 0.02
    deterministic_flip_prob: float = 0.03
    seed: int = 42


class QGapSoftmaxWrapper:
    """Native-BRL-v1 behavioral choice over the real trained action space."""

    def __init__(self, config: QGapConfig | None = None):
        self.config = config or QGapConfig()
        self.rng = np.random.default_rng(self.config.seed)

    def normalized_gap(self, q_values: npt.ArrayLike, valid_mask: npt.ArrayLike | None = None) -> float:
        q = np.asarray(q_values, dtype=float)
        mask = np.ones(q.shape, dtype=bool) if valid_mask is None else np.asarray(valid_mask, dtype=bool)
        valid = q[mask]
        if valid.size < 2:
            return float("inf")
        ordered = np.sort(valid)
        scale = float(np.median(np.abs(valid)) + 1.0e-6)
        return float((ordered[-1] - ordered[-2]) / scale)

    def _temperature(self, gap: float) -> float:
        if not np.isfinite(gap) or gap >= self.config.deterministic_gap:
            return self.config.tau_min
        if gap <= self.config.random_gap:
            return self.config.tau_max
        frac = (gap - self.config.random_gap) / (self.config.deterministic_gap - self.config.random_gap)
        return float(self.config.tau_max + frac * (self.config.tau_min - self.config.tau_max))

    def probabilities(self, q_values: npt.ArrayLike, valid_mask: npt.ArrayLike | None = None) -> np.ndarray:
        q = np.asarray(q_values, dtype=float)
        mask = np.ones(q.shape, dtype=bool) if valid_mask is None else np.asarray(valid_mask, dtype=bool)
        if not mask.any():
            mask = np.ones(q.shape, dtype=bool)
        if mask.sum() == 1:
            probs = np.zeros(q.shape, dtype=float)
            probs[np.flatnonzero(mask)[0]] = 1.0
            return probs
        gap = self.normalized_gap(q, mask)
        best = int(np.flatnonzero(mask)[np.argmax(q[mask])])
        if gap >= self.config.deterministic_gap:
            probs = np.zeros(q.shape, dtype=float)
            probs[mask] = self.config.deterministic_flip_prob / max(1, int(mask.sum()) - 1)
            probs[best] = 1.0 - self.config.deterministic_flip_prob
            return probs
        scale = float(np.median(np.abs(q[mask])) + 1.0e-6)
        z = q / scale
        masked = np.full(q.shape, -np.inf, dtype=float)
        masked[mask] = z[mask] / self._temperature(gap)
        finite = np.isfinite(masked)
        logits = masked.copy()
        logits[finite] -= np.max(logits[finite])
        exp_logits = np.zeros(q.shape, dtype=float)
        exp_logits[finite] = np.exp(logits[finite])
        total = float(exp_logits.sum())
        if total <= 0.0:
            probs = mask.astype(float)
            return probs / probs.sum()
        return exp_logits / total

    def select_action(self, q_values: npt.ArrayLike, valid_mask: npt.ArrayLike | None = None) -> int:
        probs = self.probabilities(q_values, valid_mask)
        return int(self.rng.choice(len(probs), p=probs))

