import unittest
from coverage_audit import audit,normalize
class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.m=[{"league":"L","home":"Alpha FC","away":"Beta","kickoff_istanbul":"2026-11-09T20:00:00+03:00","decision":"MODEL_ONLY_NO_ODDS"}]
        self.e=[{"id":"x","home_team":"Alpha FC","away_team":"Beta","commence_time":"2026-11-09T17:00:00Z"}]
    def test_exact(self):
        rows,c=audit(self.m,self.e);self.assertEqual(c["EXACT_TEAMS_AND_TIME_REVIEW"],1);self.assertEqual(rows[0]["approved"],"NO")
    def test_hour_offset(self):
        self.e[0]["commence_time"]="2026-11-09T18:00:00Z";self.assertEqual(audit(self.m,self.e)[1]["SAME_TEAMS_TIME_MISMATCH"],1)
    def test_date_offset(self):
        self.e[0]["commence_time"]="2026-11-12T17:00:00Z";self.assertEqual(audit(self.m,self.e)[1]["SAME_TEAMS_DIFFERENT_DATE"],1)
    def test_name_difference(self):
        self.e[0]["home_team"]="Other";self.assertEqual(audit(self.m,self.e)[1]["NO_EXACT_TEAM_PAIR"],1)
    def test_unicode(self):
        self.assertEqual(normalize("İSTANBUL"),"istanbul")
if __name__=="__main__":unittest.main()
