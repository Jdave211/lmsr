"""Invariants of the cost function. Every assertion here is an exact property."""

from __future__ import annotations

import math
import random
import unittest

from lmsr import core


class TestPrices(unittest.TestCase):
    def test_prices_sum_to_one(self):
        q = [10.0, -40.0, 3.5]
        self.assertAlmostEqual(sum(core.prices(q, 7.0)), 1.0, places=12)

    def test_seed_is_exactly_the_inverse(self):
        probs = [0.1, 0.2, 0.3, 0.4]
        q = core.seed_quantities(probs, 250.0)
        for got, want in zip(core.prices(q, 250.0), probs):
            self.assertAlmostEqual(got, want, places=12)

    def test_seed_roundtrips_at_awkward_depths(self):
        for b in (1.0, 137.0, 20_000.0, 1e7):
            probs = [0.0025, 0.0975, 0.9]
            q = core.seed_quantities(probs, b)
            for got, want in zip(core.prices(q, b), probs):
                self.assertAlmostEqual(got, want, places=10)

    def test_prices_are_monotone_in_quantity(self):
        q = [0.0, 0.0]
        p_small = core.prices([0.0, 0.0], 100.0)[0]
        p_big = core.prices([50.0, 0.0], 100.0)[0]
        self.assertGreater(p_big, p_small)

    def test_huge_quantities_do_not_overflow(self):
        q = [1e6, -1e6]
        self.assertEqual(core.prices(q, 1.0), [1.0, 0.0])
        self.assertAlmostEqual(core.cost(q, 1.0), 1e6, places=3)
        lp = core.log_prices(q, 1.0)
        self.assertAlmostEqual(lp[1], -2e6, places=3)

    def test_log_prices_survive_underflow(self):
        q = [-1e6, 0.0]
        lp = core.log_prices(q, 1.0)
        self.assertAlmostEqual(lp[0], -1e6, places=3)
        self.assertEqual(core.prices(q, 1.0)[0], 0.0)


class TestLossBound(unittest.TestCase):
    def test_uniform_prior_gives_b_ln_n(self):
        for n in (2, 3, 10):
            b = 500.0
            self.assertAlmostEqual(core.max_loss(b, [1 / n] * n), b * math.log(n), places=9)

    def test_informed_prior_increases_the_bound(self):
        # The classic b*ln(n) figure is wrong the moment the prior is informed.
        b = 100.0
        bound = core.max_loss(b, [0.001, 0.999])
        self.assertAlmostEqual(bound, -b * math.log(0.001), places=9)
        self.assertGreater(bound, 6.8 * b * math.log(2))

    def test_b_for_loss_inverts_the_bound(self):
        b = core.b_for_loss(10_000.0, 4)
        self.assertAlmostEqual(core.max_loss(b, [0.25] * 4), 10_000.0, places=5)

    def test_probabilities_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            core.check_probabilities([0.5, 0.6])

    def test_probabilities_are_not_silently_normalised(self):
        with self.assertRaises(ValueError):
            core.seed_quantities([2.0, 2.0], 100.0)

    def test_zero_probability_rejected(self):
        with self.assertRaises(ValueError):
            core.check_probabilities([0.0, 1.0])


class TestTrades(unittest.TestCase):
    def setUp(self):
        self.b = 1_000.0
        self.probs = [0.25, 0.25, 0.25, 0.25]
        self.q = core.seed_quantities(self.probs, self.b)

    def test_buy_cost_matches_the_closed_form(self):
        i, delta = 2, 300.0
        p = core.prices(self.q, self.b)[i]
        expected = self.b * math.log1p(p * math.expm1(delta / self.b))
        self.assertAlmostEqual(core.buy_cost(self.q, i, delta, self.b), expected, places=6)

    def test_shares_for_cash_inverts_buy_cost(self):
        for cash in (1.0, 50.0, 2_000.0, 50_000.0):
            delta = core.shares_for_cash(self.q, 1, cash, self.b)
            self.assertAlmostEqual(core.buy_cost(self.q, 1, delta, self.b), cash, places=6)

    def test_shares_for_refund_inverts_sell_refund(self):
        ceiling = core.max_refund(self.q, 1, self.b)
        for cash in (1.0, 50.0, ceiling * 0.5):
            delta = core.shares_for_refund(self.q, 1, cash, self.b)
            self.assertAlmostEqual(core.sell_refund(self.q, 1, delta, self.b), cash, places=6)

    def test_refund_ceiling_is_enforced(self):
        ceiling = core.max_refund(self.q, 1, self.b)
        with self.assertRaises(ValueError):
            core.shares_for_refund(self.q, 1, ceiling * 2, self.b)

    def test_selling_everything_approaches_the_ceiling(self):
        ceiling = core.max_refund(self.q, 1, self.b)
        huge = core.sell_refund(self.q, 1, 1e7, self.b)
        self.assertAlmostEqual(huge, ceiling, places=3)

    def test_path_independence_one_trade_equals_many(self):
        one = core.buy_cost(self.q, 0, 1_000.0, self.b)
        q, total = list(self.q), 0.0
        for _ in range(10):
            total += core.buy_cost(q, 0, 100.0, self.b)
            q[0] += 100.0
        self.assertAlmostEqual(one, total, places=9)

    def test_bundle_cost_is_order_independent(self):
        legs_a = [(0, 100.0), (1, 50.0), (2, 25.0)]
        legs_b = [(2, 25.0), (0, 100.0), (1, 50.0)]
        a = core.bundle_cost(self.q, legs_a, self.b)
        b = core.bundle_cost(self.q, legs_b, self.b)
        self.assertAlmostEqual(a, b, places=12)

    def test_cost_is_convex(self):
        rng = random.Random(7)
        for _ in range(50):
            q1 = [rng.uniform(-500, 500) for _ in range(3)]
            q2 = [rng.uniform(-500, 500) for _ in range(3)]
            t = rng.random()
            mid = [(1 - t) * a + t * b for a, b in zip(q1, q2)]
            lhs = core.cost(mid, 100.0)
            rhs = (1 - t) * core.cost(q1, 100.0) + t * core.cost(q2, 100.0)
            self.assertLessEqual(lhs, rhs + 1e-9)

    def test_zero_trade_costs_nothing(self):
        self.assertAlmostEqual(core.buy_cost(self.q, 0, 0.0, self.b), 0.0, places=12)

    def test_negative_b_rejected(self):
        with self.assertRaises(ValueError):
            core.cost(self.q, 0.0)


class TestNoContracts(unittest.TestCase):
    def test_no_price_is_one_minus_p(self):
        b = 1_000.0
        q = core.seed_quantities([0.3, 0.3, 0.4], b)
        for i in range(3):
            p = core.prices(q, b)[i]
            small = 1e-4  # the limit as size goes to zero; convexity is second order
            cost = core.no_cost(q, i, small, b)
            self.assertAlmostEqual(cost / small, 1 - p, places=6)

    def test_no_shares_for_cash_inverts_no_cost(self):
        b = 1_000.0
        q = core.seed_quantities([0.3, 0.3, 0.4], b)
        for cash in (10.0, 500.0, 5_000.0):
            shares = core.shares_no_for_cash(q, 0, cash, b)
            self.assertAlmostEqual(core.no_cost(q, 0, shares, b), cash, places=6)


if __name__ == "__main__":
    unittest.main()
