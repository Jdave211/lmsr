"""Cost function and quoting for the Logarithmic Market Scoring Rule.

The whole engine is one state vector: ``q``, the outstanding shares of each
outcome. The cost function

    C(q) = b * ln( sum_i exp(q_i / b) )

is a scalar potential. The cash needed for any trade is ``C(q_end) - C(q_start)``,
so cost depends only on where you end up, never on the route. That is why the
engine can be tested with exact equalities instead of tolerances, and why every
classical invariant (prices sum to one, bounded loss) is a one-line consequence
rather than a promise.

``b`` is the depth parameter. It is fixed when the market opens and never
changes. It is *not* a budget: the maker's worst-case loss is
``b * -ln(min opening probability)``, which equals ``b * ln(n)`` only when the
market opens at equal prices. Use :func:`max_loss`, not ``b``.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

__all__ = [
    "b_for_loss",
    "bundle_cost",
    "buy_cost",
    "cost",
    "log_prices",
    "max_loss",
    "max_refund",
    "prices",
    "seed_quantities",
    "sell_refund",
    "shares_for_cash",
    "shares_for_refund",
]


# -- numerics ---------------------------------------------------------------


def _logsumexp(values: Sequence[float]) -> float:
    """log(sum(exp(x))) without overflow. The only place exp() is called."""
    m = max(values)
    if m == -math.inf:
        return -math.inf
    return m + math.log(sum(math.exp(v - m) for v in values))


def _logaddexp(a: float, b: float) -> float:
    """log(exp(a) + exp(b)) without overflow."""
    if a == -math.inf:
        return b
    if b == -math.inf:
        return a
    if a < b:
        a, b = b, a
    return a + math.log1p(math.exp(b - a))


def _log_expm1(x: float) -> float:
    """log(exp(x) - 1), stable for large x."""
    if x > 50.0:
        return x + math.log1p(-math.exp(-x))
    return math.log(math.expm1(x))


def _check_b(b: float) -> None:
    if not isinstance(b, (int, float)) or not math.isfinite(b) or b <= 0:
        raise ValueError(f"b must be a finite positive number, got {b!r}")


def check_probabilities(probabilities: Iterable[float], tol: float = 1e-9) -> tuple[float, ...]:
    """Validate a probability vector. Never silently renormalises.

    A research engine that quietly rescales its inputs cannot tell you what
    price it actually traded at. Normalise at the call site and say so.
    """
    probs = tuple(float(p) for p in probabilities)
    if len(probs) < 2:
        raise ValueError("a market needs at least two outcomes")
    if any(not math.isfinite(p) or p <= 0.0 for p in probs):
        raise ValueError("every outcome needs a strictly positive probability")
    total = sum(probs)
    if abs(total - 1.0) > tol:
        raise ValueError(f"probabilities must sum to 1, got {total!r}")
    return probs


# -- the cost function ------------------------------------------------------


def cost(q: Sequence[float], b: float) -> float:
    """C(q) = b * ln(sum_i exp(q_i / b)). The state potential."""
    _check_b(b)
    if len(q) < 2:
        raise ValueError("q needs at least two outcomes")
    return b * _logsumexp([v / b for v in q])


def log_prices(q: Sequence[float], b: float) -> list[float]:
    """ln of each price. Exact even where the price itself underflows."""
    _check_b(b)
    x = [v / b for v in q]
    lse = _logsumexp(x)
    return [xi - lse for xi in x]


def prices(q: Sequence[float], b: float) -> list[float]:
    """p_i = exp(q_i / b) / sum_j exp(q_j / b). Always sums to 1."""
    return [math.exp(lp) for lp in log_prices(q, b)]


def seed_quantities(probabilities: Sequence[float], b: float) -> list[float]:
    """q_i = b * ln(p_i): the exact inverse of the price map.

    This is the only correct way to open a market at a chosen set of prices.
    It is also the whole reason a market can have an informed prior at all.
    """
    _check_b(b)
    probs = check_probabilities(probabilities)
    return [b * math.log(p) for p in probs]


def b_for_loss(max_loss_amount: float, n_outcomes: int) -> float:
    """Depth that puts the worst case at ``max_loss_amount`` from an equal prior."""
    if max_loss_amount <= 0:
        raise ValueError("max_loss_amount must be positive")
    if n_outcomes < 2:
        raise ValueError("a market needs at least two outcomes")
    return max_loss_amount / math.log(n_outcomes)


def max_loss(b: float, probabilities: Sequence[float]) -> float:
    """Worst-case maker loss: ``b * -ln(min opening probability)``.

    From a uniform prior this is ``b * ln(n)``, the figure usually quoted. With
    an informed prior it is larger, because selling a longshot cheaply is a
    position. Derivation: the maker's loss if outcome k wins is
    ``(q_k - q0_k) - (C(q) - C(q0))``; since ``C(q) >= q_k`` the first term is
    at most 0, so the loss is at most ``C(q0) - q0_k = -b * ln(p0_k)``. Take the
    worst k.
    """
    _check_b(b)
    probs = check_probabilities(probabilities)
    return -b * math.log(min(probs))


# -- trades -----------------------------------------------------------------


def buy_cost(q: Sequence[float], i: int, shares: float, b: float) -> float:
    """Cash to buy ``shares`` of outcome ``i``."""
    if shares < 0:
        raise ValueError("buy_cost needs non-negative shares; use sell_refund")
    q2 = list(q)
    q2[i] += shares
    return cost(q2, b) - cost(q, b)


def sell_refund(q: Sequence[float], i: int, shares: float, b: float) -> float:
    """Cash returned for selling ``shares`` of outcome ``i``."""
    if shares < 0:
        raise ValueError("sell_refund needs non-negative shares; use buy_cost")
    q2 = list(q)
    q2[i] -= shares
    return cost(q, b) - cost(q2, b)


def bundle_cost(q: Sequence[float], legs: Iterable[tuple[int, float]], b: float) -> float:
    """Cash to buy a vector of legs in one trade.

    A bundle is the general primitive. "NO on outcome i" is the bundle that
    buys one share of every *other* outcome; there is no special case in the
    cost function, and therefore no special case in the loss bound.
    """
    q2 = list(q)
    for i, shares in legs:
        q2[i] += shares
    return cost(q2, b) - cost(q, b)


def shares_for_cash(q: Sequence[float], i: int, cash: float, b: float) -> float:
    """Shares of outcome ``i`` bought for ``cash``. Exact inverse of buy_cost."""
    _check_b(b)
    if cash < 0:
        raise ValueError("cash must be non-negative")
    if cash == 0:
        return 0.0
    lp = log_prices(q, b)[i]
    return b * _logaddexp(0.0, _log_expm1(cash / b) - lp)


def max_refund(q: Sequence[float], i: int, b: float) -> float:
    """Cash ceiling for selling outcome ``i``: ``-b * ln(1 - p_i)``."""
    p = prices(q, b)[i]
    if p >= 1.0:
        return math.inf
    return -b * math.log1p(-p)


def shares_for_refund(q: Sequence[float], i: int, cash: float, b: float) -> float:
    """Shares of outcome ``i`` to sell for ``cash``. Exact inverse of sell_refund."""
    _check_b(b)
    if cash < 0:
        raise ValueError("cash must be non-negative")
    if cash == 0:
        return 0.0
    p = prices(q, b)[i]
    if p <= 0.0:
        raise ValueError(f"outcome {i} is worthless; nothing to sell")
    y = -math.expm1(-cash / b)  # 1 - exp(-cash / b)
    ratio = y / p
    if ratio >= 1.0:
        ceiling = max_refund(q, i, b)
        raise ValueError(
            f"cannot refund {cash}: the ceiling for this outcome is {ceiling:.6f}"
        )
    return -b * math.log1p(-ratio)


# -- bundles that are really "NO" ------------------------------------------


def no_cost(q: Sequence[float], i: int, shares: float, b: float) -> float:
    """Cash to buy ``shares`` NO contracts on outcome ``i``.

    A NO contract pays 1 if ``i`` loses. It is the bundle that buys one share of
    every other outcome, so it trades at ``1 - p_i`` exactly. No ad-hoc
    complement arithmetic, no guarantee lost.
    """
    if shares < 0:
        raise ValueError("shares must be non-negative")
    legs = [(j, shares) for j in range(len(q)) if j != i]
    return bundle_cost(q, legs, b)


def shares_no_for_cash(q: Sequence[float], i: int, cash: float, b: float) -> float:
    """NO contracts bought for ``cash``. Closed form: price is ``1 - p_i``."""
    _check_b(b)
    if cash < 0:
        raise ValueError("cash must be non-negative")
    if cash == 0:
        return 0.0
    p = prices(q, b)[i]
    complement = 1.0 - p
    if complement <= 0.0:
        raise ValueError(f"outcome {i} is certain; NO has no value")
    return b * math.log1p(math.expm1(cash / b) / complement)
