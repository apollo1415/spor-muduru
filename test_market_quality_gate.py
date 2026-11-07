import unittest
from market_quality_gate import assess
class MarketQualityGateTests(unittest.TestCase):
    def setUp(self):
        self.row={"market":"home_win","cohort":"PAIRED","n":"2709","team_brier":"0.19",
                  "league_prior_brier":"0.21","team_log_loss":"0.55","league_prior_log_loss":"0.60"}
    def test_both_scores_required(self):
        self.assertEqual(assess([self.row])[0]["status"],"TEAM_MODEL_RETROSPECTIVELY_BETTER")
        r=dict(self.row,team_log_loss="0.61")
        self.assertEqual(assess([r])[0]["status"],"NO_CONSISTENT_TEAM_MODEL_ADVANTAGE")
    def test_no_automatic_approval(self):
        self.assertEqual(assess([self.row])[0]["eligible_for_odds"],"NO")
    def test_insufficient_sample(self):
        self.assertEqual(assess([dict(self.row,n="10")])[0]["status"],"INSUFFICIENT_PAIRED_SAMPLE")
    def test_duplicate_fails_closed(self):
        self.assertEqual(assess([self.row,self.row])[0]["status"],"DUPLICATE_PAIRED_COHORT")
    def test_invalid_metric_fails_closed(self):
        self.assertEqual(assess([dict(self.row,team_brier="oops")])[0]["status"],"INVALID_METRICS")
    def test_fallback_only_not_promoted(self):
        self.assertEqual(assess([dict(self.row,cohort="FALLBACK_ONLY")]),[])
if __name__=="__main__":unittest.main()
