"""Regression tests for chronological calibration and league-level diagnostics."""
import unittest
from calibration_methods import benchmark

class CalibrationMethodsTests(unittest.TestCase):
    def rows(self, n_days=24, per_day=12):
        return [
            {"date": f"2026-01-{d:02d}", "league": "A" if i % 2 else "B",
             "home": str(i), "away": str(d),
             "probability": str(.2 + (i % 5) * .13),
             "outcome": str(int((d + i) % 3 == 0))}
            for d in range(1, n_days + 1) for i in range(per_day)
        ]

    def test_three_way_date_split_and_no_approval(self):
        result = benchmark(self.rows(), min_fit=50, min_validation=30, min_holdout=30)
        self.assertEqual(result["status"], "EVALUATED")
        self.assertLess(result["validation_start"], result["holdout_start"])
        self.assertEqual(result["fit_n"] + result["validation_n"] + result["holdout_n"], 288)
        self.assertEqual(len(result["holdout_segments"]), 2)
        self.assertEqual(result["deployment"], "RESEARCH_ONLY")

    def test_insufficient_sample_fails_closed(self):
        result = benchmark(self.rows(n_days=5, per_day=2))
        self.assertEqual(result["status"], "INSUFFICIENT_SAMPLE")

    def test_invalid_probability_fails_closed(self):
        rows = self.rows()
        rows[0]["probability"] = "1.2"
        result = benchmark(rows, min_fit=50, min_validation=30, min_holdout=30)
        self.assertEqual(result["status"], "INVALID_PROBABILITIES")

    def test_league_counts_consistent(self):
        result = benchmark(self.rows(), min_fit=50, min_validation=30, min_holdout=30)
        counts = result["league_consistency"]
        self.assertEqual(counts["evaluated"], counts["improved_both"] + counts["not_improved_both"])
        self.assertEqual(counts["evaluated"] + counts["insufficient_sample"], len(result["league_audit"]))

if __name__ == "__main__":
    unittest.main()
