import unittest
from horizon_coverage import compare
class HorizonTests(unittest.TestCase):
    def setUp(self):
        self.f=[{"league":"L","home":"Alpha","away":"Beta","kickoff_istanbul":"2026-11-10T20:00:00+03:00"}]
        self.e=[{"id":"e","home_team":"Alpha","away_team":"Beta","commence_time":"2026-11-10T17:00:00Z"}]
    def test_same(self):
        r,c=compare(self.f,self.e);self.assertEqual(c["SAME_TEAMS_WITHIN_24H"],1);self.assertEqual(r[0]["approved"],"NO")
    def test_no_pair(self):
        self.e[0]["home_team"]="Other";self.assertEqual(compare(self.f,self.e)[1]["NO_EXACT_TEAM_PAIR_IN_HORIZON"],1)
    def test_other_date(self):
        self.e[0]["commence_time"]="2026-11-20T17:00:00Z";self.assertEqual(compare(self.f,self.e)[1]["SAME_TEAMS_OTHER_DATE"],1)
if __name__=="__main__":unittest.main()
