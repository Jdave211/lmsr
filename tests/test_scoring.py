"""Scoring rules must be proper and must not round quietly."""

from __future__ import annotations

import math
import unittest

from lmsr import scoring


class TestScores(unittest.TestCase):
    def test_brier_perfect_is_zero(self):
        self.assertAlmostEqual(scoring.brier([1.0, 0.0], 0), 0.0)

    def test_brier_worst_is_two(self):
        self.assertAlmostEqual(scoring.brier([0.0, 1.0], 0), 2.0)

    def test_brier_is_proper(self):
        # Reporting the truth beats any distortion, on average.
        truth = [0.7, 0.3]
        report = [0.7, 0.3]
        lie = [0.6, 0.4]
        expected_report = sum(p * scoring.brier(report, i) for i, p in enumerate(truth))
        expected_lie = sum(p * scoring.brier(lie, i) for i, p in enumerate(truth))
        self.assertLess(expected_report, expected_lie)

    def test_log_loss_of_a_coin_flip(self):
        self.assertAlmostEqual(scoring.log_loss([0.5, 0.5], 1), math.log(2))

    def test_log_loss_is_proper(self):
        truth = [0.8, 0.2]
        report = [0.8, 0.2]
        lie = [0.7, 0.3]
        expected_report = sum(p * scoring.log_loss(report, i) for i, p in enumerate(truth))
        expected_lie = sum(p * scoring.log_loss(lie, i) for i, p in enumerate(truth))
        self.assertLess(expected_report, expected_lie)

    def test_calibration_bins(self):
        rows = scoring.calibration([0.05, 0.15, 0.95], [0, 0, 1], bins=10)
        self.assertEqual(len(rows), 3)
        self.assertAlmostEqual(rows[0]["mean_forecast"], 0.05)
        self.assertAlmostEqual(rows[0]["frequency"], 0.0)
        self.assertAlmostEqual(rows[2]["frequency"], 1.0)

    def test_calibration_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            scoring.calibration([1.2], [1])

    def test_outcome_index_validated(self):
        with self.assertRaises(ValueError):
            scoring.brier([0.5, 0.5], 2)


if __name__ == "__main__":
    unittest.main()
