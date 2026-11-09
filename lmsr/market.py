"""A market: the cost function plus the state it moves through.

Three rules keep this honest:

1. ``b`` is set once and is never defaulted, floored, or clamped.
2. The opening price is exactly the probability you passed in. If you want a
   softer prior, soften it at the call site and you will still be able to say
   what you traded at.
3. Every trade updates ``q`` through the same potential, bundles included, so
   the loss bound holds for every sequence of trades and not just for the
   simple ones.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

from . import core

__all__ = ["Market", "TradeError"]


class TradeError(ValueError):
    """Raised when a trade cannot be priced or would break an invariant."""


class Market:
    """An LMSR market with fixed depth ``b``.

    Parameters
    ----------
    outcomes:
        Names, at least two, unique.
    b:
        Depth. Required. There is no default because there is no correct
        default: the depth is a choice about how much the maker is willing to
        lose. See ``core.max_loss``.
    probabilities:
        Opening prices. Defaults to equal. Must sum to 1 and be strictly
        positive; nothing is silently rescaled.
    fee_rate:
        Fraction of traded cash charged per trade. Fees make total cost
        path-dependent by design; keep it at 0 when testing invariants.
    """

    def __init__(
        self,
        outcomes: Sequence[str],
        b: float,
        probabilities: Sequence[float] | None = None,
        fee_rate: float = 0.0,
    ) -> None:
        names = tuple(str(o) for o in outcomes)
        if len(names) < 2:
            raise ValueError("a market needs at least two outcomes")
        if len(set(names)) != len(names):
            raise ValueError("outcome names must be unique")
        if not 0.0 <= float(fee_rate) < 1.0:
            raise ValueError("fee_rate must be in [0, 1)")

        n = len(names)
        if probabilities is None:
            probabilities = [1.0 / n] * n
        probs = core.check_probabilities(probabilities)
        if len(probs) != n:
            raise ValueError("one probability per outcome")

        self.outcomes = names
        self.b = float(b)
        core._check_b(self.b)
        self.fee_rate = float(fee_rate)

        self._q = core.seed_quantities(probs, self.b)
        self._q0 = tuple(self._q)
        self._p0 = probs
        self.revenue = 0.0
        self.trades: list[dict] = []

    # -- state --------------------------------------------------------------

    @property
    def quantities(self) -> tuple[float, ...]:
        return tuple(self._q)

    @property
    def opening_probabilities(self) -> tuple[float, ...]:
        return self._p0

    @property
    def prices(self) -> tuple[float, ...]:
        return tuple(core.prices(self._q, self.b))

    @property
    def log_prices(self) -> tuple[float, ...]:
        return tuple(core.log_prices(self._q, self.b))

    @property
    def max_loss(self) -> float:
        """Worst case if traders push the market anywhere and lose."""
        return core.max_loss(self.b, self._p0)

    @property
    def worst_case_loss(self) -> float:
        """Worst case given the trades actually taken so far."""
        return max(self.pnl(o) for o in self.outcomes)

    def pnl(self, outcome: str) -> float:
        """The maker's loss if ``outcome`` wins. Positive means the maker loses."""
        i = self._idx(outcome)
        payout = self._q[i] - self._q0[i]
        return payout - self.revenue

    def _idx(self, outcome: str | int) -> int:
        if isinstance(outcome, int):
            if not 0 <= outcome < len(self.outcomes):
                raise IndexError(outcome)
            return outcome
        try:
            return self.outcomes.index(outcome)
        except ValueError:
            raise TradeError(f"unknown outcome {outcome!r}") from None

    def _legs(self, legs: Mapping[str | int, float]) -> list[tuple[int, float]]:
        return [(self._idx(k), float(v)) for k, v in legs.items()]

    # -- quoting ------------------------------------------------------------

    def quote(self, outcome: str | int, shares: float) -> float:
        """Cash to buy ``shares`` (negative sells). Fee excluded."""
        i = self._idx(outcome)
        if shares >= 0:
            return core.buy_cost(self._q, i, shares, self.b)
        return -core.sell_refund(self._q, i, -shares, self.b)

    def quote_bundle(self, legs: Mapping[str | int, float]) -> float:
        """Cash to buy a vector of legs (negative sells). Fee excluded."""
        return core.bundle_cost(self._q, self._legs(legs), self.b)

    def quote_no(self, outcome: str | int, shares: float) -> float:
        """Cash to buy ``shares`` NO contracts (negative sells). Fee excluded."""
        i = self._idx(outcome)
        if shares >= 0:
            return core.no_cost(self._q, i, shares, self.b)
        legs = [(j, shares) for j in range(len(self._q)) if j != i]
        return core.bundle_cost(self._q, legs, self.b)

    # -- execution ----------------------------------------------------------

    def buy(self, outcome: str | int, shares: float) -> dict:
        """Buy ``shares`` at the cost function's price, plus fee."""
        if shares <= 0:
            raise TradeError("shares must be positive")
        i = self._idx(outcome)
        before = self.prices
        gross = core.buy_cost(self._q, i, shares, self.b)
        fee = gross * self.fee_rate
        self._q[i] += shares
        self.revenue += gross
        return self._record("buy", i, shares, gross, fee, before)

    def sell(self, outcome: str | int, shares: float) -> dict:
        """Sell ``shares`` for the cost function's refund, minus fee."""
        if shares <= 0:
            raise TradeError("shares must be positive")
        i = self._idx(outcome)
        before = self.prices
        gross = core.sell_refund(self._q, i, shares, self.b)
        fee = gross * self.fee_rate
        self._q[i] -= shares
        self.revenue -= gross
        return self._record("sell", i, shares, -gross, fee, before)

    def buy_for_cash(self, outcome: str | int, cash: float) -> dict:
        """Spend exactly ``cash``, fee included, and receive shares."""
        if cash <= 0:
            raise TradeError("cash must be positive")
        net = cash / (1.0 + self.fee_rate)
        i = self._idx(outcome)
        shares = core.shares_for_cash(self._q, i, net, self.b)
        return self.buy(outcome, shares)

    def sell_for_cash(self, outcome: str | int, cash: float) -> dict:
        """Sell enough shares to receive exactly ``cash`` after fee."""
        if cash <= 0:
            raise TradeError("cash must be positive")
        gross = cash / (1.0 - self.fee_rate)
        i = self._idx(outcome)
        shares = core.shares_for_refund(self._q, i, gross, self.b)
        return self.sell(outcome, shares)

    def buy_bundle(self, legs: Mapping[str | int, float]) -> dict:
        """Buy several legs as one trade. Negative shares sell."""
        idx_legs = self._legs(legs)
        if not idx_legs:
            raise TradeError("a bundle needs at least one leg")
        gross = core.bundle_cost(self._q, idx_legs, self.b)
        fee = abs(gross) * self.fee_rate
        before = self.prices
        for i, shares in idx_legs:
            self._q[i] += shares
        self.revenue += gross
        return self._record("bundle", None, sum(s for _, s in idx_legs), gross, fee, before)

    def buy_no(self, outcome: str | int, shares: float) -> dict:
        """Buy ``shares`` NO contracts. Each pays 1 if ``outcome`` loses."""
        if shares <= 0:
            raise TradeError("shares must be positive")
        i = self._idx(outcome)
        legs = [(j, shares) for j in range(len(self._q)) if j != i]
        gross = core.bundle_cost(self._q, legs, self.b)
        fee = gross * self.fee_rate
        before = self.prices
        for j, s in legs:
            self._q[j] += s
        self.revenue += gross
        return self._record("buy_no", i, shares, gross, fee, before)

    def buy_no_for_cash(self, outcome: str | int, cash: float) -> dict:
        """Spend ``cash`` on NO contracts of ``outcome``."""
        if cash <= 0:
            raise TradeError("cash must be positive")
        net = cash / (1.0 + self.fee_rate)
        i = self._idx(outcome)
        shares = core.shares_no_for_cash(self._q, i, net, self.b)
        return self.buy_no(outcome, shares)

    # -- bookkeeping --------------------------------------------------------

    def _record(self, action: str, i: int | None, shares: float, gross: float,
                fee: float, before: Sequence[float]) -> dict:
        trade = {
            "action": action,
            "outcome": None if i is None else self.outcomes[i],
            "index": i,
            "shares": shares,
            "cash": gross + fee if gross >= 0 else gross - fee,
            "gross": gross,
            "fee": fee,
            "prices_before": tuple(before),
            "prices_after": self.prices,
        }
        self.trades.append(trade)
        return trade

    def __repr__(self) -> str:
        prices = ", ".join(
            f"{o}={p:.3f}" for o, p in zip(self.outcomes, self.prices)
        )
        return f"Market(b={self.b:g}, n={len(self.outcomes)}, {prices})"
