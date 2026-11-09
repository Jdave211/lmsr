"""Proper scoring rules, for judging prices rather than P&L.

A market price is a forecast. Score it like one. Brier and log loss are proper:
they are minimised, in expectation, by the true probability, so a market that
games them is a market that is wrong. That is the same reason the deflated
Sharpe exists on the returns side.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

__all__ = ["brier", "log_loss", "calibration", "one_hot"]


def one_hot(outcome: int, n: int) -> list[float]:
    if not 0 <= outcome < n:
        raise ValueError("outcome index out of range")
    vec = [0.0] * n
    vec[outcome] = 1.0
    return vec


def brier(probabilities: Sequence[float], outcome: int) -> float:
    """Multiclass Brier score. 0 is perfect, 2 is worst."""
    y = one_hot(outcome, len(probabilities))
    return sum((p - t) ** 2 for p, t in zip(probabilities, y))


def log_loss(probabilities: Sequence[float], outcome: int, eps: float = 1e-12) -> float:
    """Negative log likelihood of the realised outcome."""
    if not 0 <= outcome < len(probabilities):
        raise ValueError("outcome index out of range")
    p = max(float(probabilities[outcome]), eps)
    return -math.log(p)


def calibration(
    probabilities: Iterable[float],
    outcomes: Iterable[int],
    bins: int = 10,
) -> list[dict]:
    """Average forecast vs realised frequency, per probability bin.

    Each row is one bin: how often we said ``p`` and how often it happened.
    A calibrated forecaster has ``mean_forecast ~= frequency``.
    """
    if bins < 1:
        raise ValueError("bins must be positive")
    rows = [[] for _ in range(bins)]
    for p, y in zip(probabilities, outcomes):
        p = float(p)
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"probability out of range: {p}")
        idx = min(int(p * bins), bins - 1)
        rows[idx].append((p, int(y)))

    out = []
    for idx, items in enumerate(rows):
        if not items:
            continue
        ps = [p for p, _ in items]
        ys = [y for _, y in items]
        out.append(
            {
                "bin": idx,
                "lo": idx / bins,
                "hi": (idx + 1) / bins,
                "n": len(items),
                "mean_forecast": sum(ps) / len(ps),
                "frequency": sum(ys) / len(ys),
            }
        )
    return out
