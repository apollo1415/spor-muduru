import unittest
from datetime import datetime,timezone
from league_prior_fallback import prior,fallback
class LeaguePriorFallbackTests(unittest.TestCase):
    def setUp(self):
        self.history=[{"date":"2026-10-01","ft_home":"2","ft_away":"1"} for _ in range(20)]
        self.model={"league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-10T20:00:00+03:00","decision":"INSUFFICIENT_HISTORY"}
        self.now=datetime(2026,11,7,tzinfo=timezone.utc)
    def test_minimum_sample(self):
        self.assertIsNone(prior(self.history[:19],"2026-11-07"))
        self.assertEqual(prior(self.history,"2026-11-07"),(2,1,20))
    def test_no_future_leakage(self):
        self.assertIsNone(prior([dict(x,date="2026-11-08") for x in self.history],"2026-11-07"))
    def test_research_only(self):
        r=fallback([self.model],{"L":self.history},self.now)[0]
        self.assertEqual(r["baseline_status"],"LEAGUE_PRIOR_RESEARCH_ONLY")
        self.assertEqual(r["eligible_for_odds"],"NO")
        self.assertAlmostEqual(r["p_home"]+r["p_draw"]+r["p_away"],1,places=3)
    def test_missing_prior(self):
        r=fallback([self.model],{"L":[]},self.now)[0]
        self.assertEqual(r["baseline_status"],"INSUFFICIENT_LEAGUE_HISTORY")
        self.assertNotIn("p_home",r)
    def test_only_insufficient_models(self):
        self.assertEqual(fallback([dict(self.model,decision="MODEL_ONLY_NO_ODDS")],{"L":self.history},self.now),[])
if __name__=="__main__":unittest.main()
