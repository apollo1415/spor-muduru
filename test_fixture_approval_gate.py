import unittest
from fixture_approval_gate import gate

class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.q={"event_id":"evt1","provider_home":"Alpha","provider_away":"Beta","provider_sport":"soccer_epl",
                "provider_kickoff_utc":"2026-11-08T14:00:00Z","source_league":"ENG_1_premier-league",
                "source_home":"Alpha","source_away":"Beta","source_kickoff_istanbul":"2026-11-08T17:00:00+03:00",
                "league_review":"LEAGUE_MATCH","review_status":"REVIEW_TIME_AND_LEAGUE","delta_minutes":"0"}
        self.e={"home":"Alpha","away":"Beta","league":"soccer_epl","kickoff_utc":"2026-11-08T14:00:00Z","source_url":"https://example.org"}
        self.a={"event_id":"evt1","decision":"APPROVE","provider_home":"Alpha","provider_away":"Beta",
                "league":"ENG_1_premier-league","home":"Alpha","away":"Beta","kickoff_istanbul":"2026-11-08T17:00:00+03:00"}
    def test_no_manual_approvals(self):
        self.assertEqual(gate([self.q],[self.e],[]),([],[]))
    def test_exact_explicit_approval(self):
        ok,bad=gate([self.q],[self.e],[self.a]);self.assertEqual(len(ok),1);self.assertEqual(bad,[])
    def test_evidence_alone_does_not_approve(self):
        ok,bad=gate([self.q],[self.e],[dict(self.a,decision="PENDING")]);self.assertEqual(ok,[]);self.assertEqual(len(bad),1)
    def test_mismatch_fails_closed(self):
        ok,bad=gate([self.q],[self.e],[dict(self.a,home="Wrong")]);self.assertEqual(ok,[]);self.assertEqual(len(bad),1)
    def test_duplicate_fails_closed(self):
        ok,bad=gate([self.q,self.q],[self.e],[self.a]);self.assertEqual(ok,[]);self.assertEqual(len(bad),1)
    def test_wrong_evidence_fails_closed(self):
        ok,bad=gate([self.q],[dict(self.e,kickoff_utc="2026-11-09T14:00:00Z")],[self.a]);self.assertEqual(ok,[]);self.assertEqual(len(bad),1)
if __name__=="__main__":unittest.main()
