import unittest
from fixture_verification_checklist import checklist
class FixtureChecklistTests(unittest.TestCase):
    def setUp(self):
        self.q={"event_id":"1","provider_sport":"soccer_epl","provider_home":"A","provider_away":"B",
                "provider_kickoff_utc":"2026-11-08T14:00:00Z","source_league":"eng.1","source_home":"A","source_away":"B",
                "source_kickoff_istanbul":"2026-11-08T17:00:00+03:00","delta_minutes":"0",
                "review_status":"REVIEW_TIME_AND_LEAGUE","league_review":"LEAGUE_MATCH"}
        self.e={"league":"soccer_epl","home":"A","away":"B","kickoff_utc":"2026-11-08T14:00:00Z","source_url":"https://example.org"}
    def test_snapshot_does_not_approve(self):
        r=checklist([self.q],[self.e])[0]
        self.assertEqual(r["evidence_snapshot_match"],"YES")
        self.assertEqual(r["manual_approval"],"NO")
        self.assertEqual(r["independent_live_verification"],"NOT_DONE")
    def test_missing_evidence(self):
        r=checklist([self.q],[])[0]
        self.assertIn("EVIDENCE_MISSING_OR_AMBIGUOUS",r["blocking_reason"])
    def test_kickoff_mismatch(self):
        r=checklist([dict(self.q,delta_minutes="120")],[self.e])[0]
        self.assertIn("KICKOFF_DISCREPANCY",r["blocking_reason"])
    def test_ambiguous_evidence(self):
        r=checklist([self.q],[self.e,self.e])[0]
        self.assertEqual(r["evidence_snapshot_match"],"NO")
if __name__=="__main__":unittest.main()
