import unittest
from odds_discovery import candidates
class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.m=[{"league":"L","home":"Alpha FC","away":"Beta","kickoff_istanbul":"2026-11-09T20:00:00+03:00","decision":"MODEL_ONLY_NO_ODDS"}]
        self.e=[{"id":"x","home_team":"Alpha FC","away_team":"Beta","commence_time":"2026-11-09T17:00:00Z"}]
    def test_candidate_not_approved(self):
        r=candidates(self.m,self.e,"soccer_test");self.assertEqual(len(r),1);self.assertEqual(r[0]["status"],"REVIEW_REQUIRED_NOT_APPROVED")
    def test_wrong_date(self):
        self.e[0]["commence_time"]="2026-11-10T17:00:00Z";self.assertEqual(candidates(self.m,self.e,"soccer_test"),[])
    def test_wrong_team(self):
        self.e[0]["away_team"]="Gamma";self.assertEqual(candidates(self.m,self.e,"soccer_test"),[])
    def test_started_excluded(self):
        self.m[0]["decision"]="STARTED_OR_PAST";self.assertEqual(candidates(self.m,self.e,"soccer_test"),[])
if __name__=="__main__":unittest.main()
