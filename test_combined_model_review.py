import unittest
from combined_model_review import combine
class CombinedModelTests(unittest.TestCase):
    def setUp(self):
        self.r={"event_id":"x","provider_home":"Alias A","provider_away":"Alias B","source_home":"A","source_away":"B",
                "source_league":"L","kickoff_istanbul":"2026-11-10T20:00:00+03:00","model_status":"INSUFFICIENT_HISTORY","reason":"INSUFFICIENT_MODEL_HISTORY"}
        self.f={"league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-10T20:00:00+03:00",
                "baseline_status":"LEAGUE_PRIOR_RESEARCH_ONLY","p_home":"0.4","p_draw":"0.3","p_away":"0.3"}
    def test_fallback_uses_source_names_and_stays_unapproved(self):
        row=combine([self.r],[self.f])[0]
        self.assertEqual(row["research_model"],"LEAGUE_PRIOR_RESEARCH")
        self.assertEqual(row["eligible_for_odds"],"NO")
        self.assertEqual(row["p_home"],"0.4")
    def test_standard_precedence(self):
        r=dict(self.r,reason="MODEL_AVAILABLE_MANUAL_APPROVAL_REQUIRED",p_home="0.6")
        row=combine([r],[self.f])[0]
        self.assertEqual(row["research_model"],"STANDARD_RESEARCH")
        self.assertEqual(row["p_home"],"0.6")
    def test_no_fallback(self):
        self.assertEqual(combine([self.r],[])[0]["research_model"],"NONE")
    def test_duplicate_fallback_fails_closed(self):
        row=combine([self.r],[self.f,self.f])[0]
        self.assertEqual(row["research_model"],"NONE")
        self.assertEqual(row["fallback_status"],"DUPLICATE_FALLBACK")
if __name__=="__main__":unittest.main()
