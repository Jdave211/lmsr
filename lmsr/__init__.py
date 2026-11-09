"""A self-contained LMSR market maker.

Exact prices, a bounded worst case, and property tests that assert equalities
instead of tolerances. No framework, no database, no product layer.
"""

from .core import (
    b_for_loss,
    bundle_cost,
    buy_cost,
    cost,
    log_prices,
    max_loss,
    max_refund,
    no_cost,
    prices,
    seed_quantities,
    sell_refund,
    shares_for_cash,
    shares_for_refund,
    shares_no_for_cash,
)
from .market import Market, TradeError
from .scoring import brier, calibration, log_loss

__version__ = "0.1.0"

__all__ = [
    "Market",
    "TradeError",
    "b_for_loss",
    "brier",
    "bundle_cost",
    "buy_cost",
    "calibration",
    "cost",
    "log_loss",
    "log_prices",
    "max_loss",
    "max_refund",
    "no_cost",
    "prices",
    "seed_quantities",
    "sell_refund",
    "shares_for_cash",
    "shares_for_refund",
    "shares_no_for_cash",
]
