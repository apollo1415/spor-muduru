import unittest
from matching_diagnostics import diagnose
class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.m=[{"league":"L","home":"Alpha","away":"Beta","kickoff_istanbul":"2026-11-09T20:00:00+03:00","decision":"MODEL_ONLY_NO_ODDS"}]
        self.e=[{"id":"1","home_team":"Alpha","away_team":"Beta","commence_time":"2026-11-09T17:00:00Z"}]
    def test_candidate(self):
        _,c=diagnose(self.m,self.e);self.assertEqual(c["CANDIDATE_AVAILABLE"],1)
    def test_name_mismatch(self):
        self.e[0]["home_team"]="Different";_,c=diagnose(self.m,self.e);self.assertEqual(c["TEAM_NAME_MISMATCH"],1)
    def test_kickoff_mismatch(self):
        self.e[0]["commence_time"]="2026-11-09T18:00:00Z";_,c=diagnose(self.m,self.e);self.assertEqual(c["KICKOFF_MISMATCH_OVER_30M"],1)
    def test_no_day(self):
        self.e[0]["commence_time"]="2026-11-15T17:00:00Z";_,c=diagnose(self.m,self.e);self.assertEqual(c["NO_MATCH_WITHIN_24H"],1)
    def test_no_eligible(self):
        self.m[0]["decision"]="STARTED_OR_PAST";_,c=diagnose(self.m,self.e);self.assertEqual(c["no_eligible_modelled_matches"],1)
if __name__=="__main__":unittest.main()
