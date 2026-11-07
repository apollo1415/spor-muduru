import unittest
from fixture_review_report import render
class ReportTests(unittest.TestCase):
    def test_empty(self):
        self.assertIn("eşleşme bulunamadı",render([]))
    def test_details_and_no_approval(self):
        r={"provider_home":"Alpha","provider_away":"Beta","provider_sport":"soccer_epl","source_league":"england-premier-league","source_home":"Alpha","source_away":"Beta","provider_kickoff_utc":"2026-11-10T17:00:00Z","source_kickoff_istanbul":"2026-11-10T20:00:00+03:00","delta_minutes":"0","league_review":"LEAGUE_MAPPING_MISSING","time_review":"TIME_WITHIN_30M_UNVERIFIED","source_pairs_for_event":"1","provider_events_for_source":"1"}
        s=render([r]);self.assertIn("soccer_epl",s);self.assertIn("england-premier-league",s);self.assertIn("ONAY YOK",s)
if __name__=="__main__":unittest.main()
