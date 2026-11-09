"""A tiny trader simulation, used by the depth study and the examples.

Traders are deliberately simple: each holds a noisy belief around the truth and
spends a fixed budget on the outcome it thinks is most underpriced. That is
enough to show the only thing the study needs to show — that depth buys
accuracy at a price.
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from .market import Market
from .scoring import brier

__all__ = ["perturb", "run_market"]

_EPS = 1e-9


def perturb(probabilities: Sequence[float], noise: float, rng: random.Random) -> list[float]:
    """A noisy belief: multiply by log-normal shocks, then renormalise."""
    if noise < 0:
        raise ValueError("noise must be non-negative")
    raw = [p * math.exp(rng.gauss(0.0, noise)) for p in probabilities]
    total = sum(raw)
    return [p / total for p in raw]


def run_market(
    truth: Sequence[float],
    b: float,
    traders: int = 20,
    noise: float = 0.5,
    budget: float | None = None,
    fee_rate: float = 0.0,
    seed: int = 0,
) -> dict:
    """Open at uniform, let ``traders`` trade, and score the result.

    ``budget`` defaults to ``b / 50``, small enough that twenty traders move the
    price materially without exhausting the maker's capacity.
    """
    if traders < 1:
        raise ValueError("traders must be positive")
    probs = list(truth)
    total = sum(probs)
    if abs(total - 1.0) > 1e-9:
        probs = [p / total for p in probs]
    n = len(probs)
    if budget is None:
        budget = b / 50.0

    rng = random.Random(seed)
    market = Market(
        outcomes=[f"O{i}" for i in range(n)],
        b=b,
        probabilities=None,
        fee_rate=fee_rate,
    )

    for _ in range(traders):
        belief = perturb(probs, noise, rng)
        edges = [belief[i] - market.prices[i] for i in range(n)]
        i = max(range(n), key=lambda k: edges[k])
        if edges[i] <= 0:
            continue
        try:
            market.buy_for_cash(i, budget)
        except ValueError:
            continue

    final = market.prices
    expected_brier = sum(t * brier(final, k) for k, t in enumerate(probs))
    return {
        "b": b,
        "brier": expected_brier,
        "max_abs_error": max(abs(p - t) for p, t in zip(final, probs)),
        "worst_case_loss": market.worst_case_loss,
        "max_loss": market.max_loss,
        "volume": market.revenue,
        "prices": final,
        "truth": probs,
    }
