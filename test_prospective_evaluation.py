"""Tests for archived prospective forecast evaluation."""
import unittest
from datetime import datetime, timezone
from prospective_evaluation import evaluate

class ProspectiveEvaluationTests(unittest.TestCase):
    def forecast(self, captured="2026-11-07T10:00:00+00:00"):
        return {"predictions": [{
            "league": "L", "home": "A", "away": "B",
            "kickoff_istanbul": "2026-11-07T18:00:00+03:00",
            "captured_at_utc": captured,
            "p_home": .5, "p_draw": .25, "p_away": .25,
            "p_over25": .6, "p_btts": .7
        }]}
    def results(self):
        return [{"league": "L", "date": "2026-11-07", "home": "A", "away": "B",
                 "ft_home": "2", "ft_away": "1"}]
    def test_scores_all_five_markets(self):
        r = evaluate(self.forecast(), self.results(), datetime(2026,11,8,tzinfo=timezone.utc))
        self.assertEqual(r["scored_matches"], 1)
        self.assertEqual(r["scored_market_rows"], 5)
        self.assertEqual(r["markets"]["over25"]["observed_rate"], 1)
        self.assertEqual(r["approved_for_betting"], 0)
    def test_never_scores_after_kickoff_capture(self):
        r = evaluate(self.forecast("2026-11-07T16:00:00+00:00"),
                     self.results(), datetime(2026,11,8,tzinfo=timezone.utc))
        self.assertEqual(r["scored_matches"], 0)
        self.assertEqual(r["skipped"]["not_provably_prematch"], 1)
    def test_does_not_score_unplayed(self):
        r = evaluate(self.forecast(), self.results(), datetime(2026,11,7,12,tzinfo=timezone.utc))
        self.assertEqual(r["scored_matches"], 0)
        self.assertEqual(r["skipped"]["not_started"], 1)
    def test_ambiguous_result_fails_closed(self):
        r = evaluate(self.forecast(), self.results()*2, datetime(2026,11,8,tzinfo=timezone.utc))
        self.assertEqual(r["scored_matches"], 0)
        self.assertEqual(r["skipped"]["missing_or_ambiguous_result"], 1)

if __name__ == "__main__":
    unittest.main()
