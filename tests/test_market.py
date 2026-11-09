"""Market-level invariants, including the six fixes to the original engine."""

from __future__ import annotations

import math
import random
import unittest

from lmsr.market import Market, TradeError


class TestOpening(unittest.TestCase):
    def test_opening_prices_are_exactly_the_prior(self):
        probs = [0.55, 0.30, 0.15]
        m = Market(["A", "B", "C"], b=2_500.0, probabilities=probs)
        for got, want in zip(m.prices, probs):
            self.assertAlmostEqual(got, want, places=12)

    def test_b_is_required(self):
        # Fix 1: no silent default, and no floor that overrides the caller.
        with self.assertRaises(TypeError):
            Market(["A", "B"])  # type: ignore[call-arg]

    def test_small_b_is_honoured(self):
        m = Market(["A", "B"], b=1.0)
        self.assertEqual(m.b, 1.0)
        self.assertAlmostEqual(m.max_loss, math.log(2), places=12)

    def test_prior_is_not_softened(self):
        # Fix 4: what you ask for is what you get. No blend toward equal.
        m = Market(["A", "B"], b=20_000.0, probabilities=[0.0025, 0.9975])
        self.assertAlmostEqual(m.prices[0], 0.0025, places=12)

    def test_bad_probabilities_rejected(self):
        with self.assertRaises(ValueError):
            Market(["A", "B"], b=100.0, probabilities=[0.5, 0.6])
        with self.assertRaises(ValueError):
            Market(["A", "B"], b=100.0, probabilities=[0.0, 1.0])


class TestLoss(unittest.TestCase):
    def test_max_loss_is_the_prior_bound_not_b(self):
        # Fix 2: b is depth, not the amount at risk.
        m = Market(["A", "B"], b=20_000.0)
        self.assertAlmostEqual(m.max_loss, 20_000.0 * math.log(2), places=6)
        self.assertNotAlmostEqual(m.max_loss, 20_000.0)

    def test_informed_prior_raises_the_bound(self):
        m = Market(["longshot", "favourite"], b=20_000.0, probabilities=[0.001, 0.999])
        self.assertAlmostEqual(m.max_loss, -20_000.0 * math.log(0.001), places=6)

    def test_random_trades_never_break_the_bound(self):
        # Fix 5 + 6: bundles included, any order, still bounded.
        rng = random.Random(11)
        m = Market(["A", "B", "C", "D"], b=500.0, probabilities=[0.4, 0.3, 0.2, 0.1])
        for _ in range(200):
            kind = rng.choice(["buy", "sell", "bundle", "no"])
            if kind == "buy":
                m.buy(rng.randrange(4), rng.uniform(1, 40))
            elif kind == "sell":
                m.sell(rng.randrange(4), rng.uniform(1, 20))
            elif kind == "bundle":
                legs = {rng.randrange(4): rng.uniform(-10, 30) for _ in range(2)}
                m.buy_bundle(legs)
            else:
                m.buy_no(rng.randrange(4), rng.uniform(1, 25))
            self.assertLessEqual(m.worst_case_loss, m.max_loss + 1e-6)

    def test_worst_case_loss_is_achieved_by_the_winning_outcome(self):
        m = Market(["A", "B"], b=1_000.0)
        m.buy("A", 400.0)
        self.assertAlmostEqual(m.pnl("A"), m.worst_case_loss, places=9)
        self.assertLess(m.pnl("B"), m.pnl("A"))

    def test_revenue_matches_the_cost_function(self):
        m = Market(["A", "B", "C"], b=300.0)
        m.buy("B", 120.0)
        m.sell("C", 40.0)
        from lmsr.core import cost
        expected = cost(m.quantities, m.b) - cost(m._q0, m.b)
        self.assertAlmostEqual(m.revenue, expected, places=9)


class TestPathIndependence(unittest.TestCase):
    def test_one_trade_equals_ten(self):
        # Fix 6: the property the bisection code had no test for.
        a = Market(["A", "B"], b=800.0)
        b = Market(["A", "B"], b=800.0)
        a.buy("A", 1_000.0)
        for _ in range(10):
            b.buy("A", 100.0)
        self.assertAlmostEqual(a.revenue, b.revenue, places=9)
        for x, y in zip(a.quantities, b.quantities):
            self.assertAlmostEqual(x, y, places=9)

    def test_bundle_order_does_not_matter(self):
        a = Market(["A", "B", "C"], b=900.0)
        b = Market(["A", "B", "C"], b=900.0)
        a.buy_bundle({"A": 100.0, "B": 50.0, "C": 25.0})
        for name, shares in (("C", 25.0), ("A", 100.0), ("B", 50.0)):
            b.buy(name, shares)
        self.assertAlmostEqual(a.revenue, b.revenue, places=9)

    def test_sell_path_independence(self):
        a = Market(["A", "B"], b=1_200.0)
        b = Market(["A", "B"], b=1_200.0)
        a.sell("A", 600.0)
        for _ in range(6):
            b.sell("A", 100.0)
        self.assertAlmostEqual(a.revenue, b.revenue, places=9)


class TestNo(unittest.TestCase):
    def test_binary_no_is_the_other_outcome(self):
        # Fix 5: NO is a bundle, not special arithmetic.
        a = Market(["A", "B"], b=1_000.0)
        b = Market(["A", "B"], b=1_000.0)
        a.buy_no("A", 250.0)
        b.buy("B", 250.0)
        self.assertAlmostEqual(a.revenue, b.revenue, places=9)
        for x, y in zip(a.quantities, b.quantities):
            self.assertAlmostEqual(x, y, places=9)

    def test_no_pays_one_per_contract(self):
        m = Market(["A", "B", "C"], b=1_000.0)
        trade = m.buy_no("A", 120.0)
        cost = trade["gross"] + trade["fee"]
        # Each NO contract pays 1 if any other outcome wins.
        self.assertAlmostEqual(m.pnl("B"), 120.0 - cost, places=9)
        self.assertAlmostEqual(m.pnl("C"), 120.0 - cost, places=9)
        # If A wins, the maker keeps the premium.
        self.assertAlmostEqual(m.pnl("A"), -cost, places=9)

    def test_no_cost_per_share_is_one_minus_p(self):
        m = Market(["A", "B", "C"], b=10_000.0)
        p = m.prices[0]
        small = 0.05
        cost = m.quote_no("A", small)
        self.assertAlmostEqual(cost / small, 1 - p, places=5)

    def test_buy_no_for_cash_spends_it(self):
        m = Market(["A", "B", "C"], b=5_000.0)
        trade = m.buy_no_for_cash("A", 300.0)
        self.assertAlmostEqual(trade["gross"] + trade["fee"], 300.0, places=6)


class TestFees(unittest.TestCase):
    def test_buy_fee_is_charged_once(self):
        m = Market(["A", "B"], b=1_000.0, fee_rate=0.02)
        t = m.buy("A", 100.0)
        self.assertAlmostEqual(t["fee"], t["gross"] * 0.02, places=12)

    def test_buy_for_cash_spends_exactly_the_cash(self):
        m = Market(["A", "B"], b=1_000.0, fee_rate=0.02)
        t = m.buy_for_cash("A", 500.0)
        self.assertAlmostEqual(t["gross"] + t["fee"], 500.0, places=6)

    def test_sell_for_cash_receives_exactly_the_cash(self):
        m = Market(["A", "B"], b=1_000.0, fee_rate=0.02)
        m.buy("A", 1_000.0)
        before = m.revenue
        m.sell_for_cash("A", 100.0)
        self.assertAlmostEqual(before - m.revenue, 100.0 / 0.98, places=6)


class TestValidation(unittest.TestCase):
    def test_duplicate_outcomes_rejected(self):
        with self.assertRaises(ValueError):
            Market(["A", "A"], b=100.0)

    def test_unknown_outcome_rejected(self):
        m = Market(["A", "B"], b=100.0)
        with self.assertRaises(TradeError):
            m.buy("Z", 10.0)

    def test_fee_rate_validated(self):
        with self.assertRaises(ValueError):
            Market(["A", "B"], b=100.0, fee_rate=1.0)

    def test_negative_trade_rejected(self):
        m = Market(["A", "B"], b=100.0)
        with self.assertRaises(TradeError):
            m.buy("A", -1.0)

    def test_history_is_recorded(self):
        m = Market(["A", "B"], b=100.0)
        m.buy("A", 10.0)
        m.sell("A", 5.0)
        self.assertEqual([t["action"] for t in m.trades], ["buy", "sell"])
        self.assertEqual(m.trades[0]["prices_before"], m.opening_probabilities)


if __name__ == "__main__":
    unittest.main()
