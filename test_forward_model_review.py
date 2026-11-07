import unittest
from forward_model_review import reconcile
class ForwardModelReviewTests(unittest.TestCase):
    def setUp(self):
        self.q={"event_id":"e1","provider_sport":"soccer_epl","provider_home":"Alpha","provider_away":"Beta",
                "source_league":"L","source_home":"Alpha","source_away":"Beta",
                "source_kickoff_istanbul":"2026-11-09T20:00:00+03:00",
                "delta_minutes":"0","league_review":"LEAGUE_MATCH","review_status":"REVIEW_TIME_AND_LEAGUE"}
        self.m={"league":"L","home":"Alpha","away":"Beta","kickoff_istanbul":"2026-11-09T20:00:00+03:00",
                "decision":"MODEL_ONLY_NO_ODDS","p_home":"0.45","p_draw":"0.30","p_away":"0.25"}
    def test_exact_model_is_not_approved(self):
        r=reconcile([self.q],[self.m])[0]
        self.assertEqual(r["reason"],"MODEL_AVAILABLE_MANUAL_APPROVAL_REQUIRED")
        self.assertEqual(r["eligible_for_odds"],"NO")
        self.assertEqual(r["p_home"],"0.45")
    def test_missing_model(self):
        self.assertEqual(reconcile([self.q],[])[0]["reason"],"NO_EXACT_FORWARD_MODEL")
    def test_duplicate_model(self):
        self.assertEqual(reconcile([self.q],[self.m,self.m])[0]["reason"],"DUPLICATE_MODEL")
    def test_insufficient_history(self):
        self.assertEqual(reconcile([self.q],[dict(self.m,decision="INSUFFICIENT_HISTORY")])[0]["reason"],"INSUFFICIENT_MODEL_HISTORY")
    def test_league_mismatch(self):
        self.assertEqual(reconcile([dict(self.q,league_review="LEAGUE_MISMATCH")],[self.m])[0]["reason"],"LEAGUE_OR_IDENTITY_REVIEW_REQUIRED")
    def test_kickoff_delta(self):
        self.assertEqual(reconcile([dict(self.q,delta_minutes="90")],[self.m])[0]["reason"],"KICKOFF_REVIEW_REQUIRED")
if __name__=="__main__":unittest.main()
