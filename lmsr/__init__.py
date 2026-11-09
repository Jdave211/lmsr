"""A numerically honest LMSR market maker.

Extracted from probable.fun, where the mechanism was correct in spirit and
coupled to a FastAPI app. This is the mechanism alone: no framework, no
database, no hidden transforms.
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
