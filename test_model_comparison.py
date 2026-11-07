import unittest
from model_comparison import evaluate_pair,paired_summary
class ModelComparisonTests(unittest.TestCase):
    def setUp(self):
        self.results=[]
        for d in range(1,27):
            self.results.append({"date":"2026-10-%02d"%d,"home":"A","away":"B","ft_home":"2","ft_away":"1"})
    def test_strictly_prior_days(self):
        rows=evaluate_pair(self.results,"L","2026-10-26")
        self.assertTrue(rows)
        self.assertTrue(all(r["date"]<"2026-10-26" for r in rows))
        self.assertTrue(all(r["method"]=="LEAGUE_PRIOR" for r in rows if r["date"]=="2026-10-21"))
    def test_future_results_do_not_leak(self):
        before=evaluate_pair(self.results[:25],"L","2026-10-26")
        modified=self.results[:25]+[dict(self.results[25],ft_home="100")]
        self.assertEqual(before,evaluate_pair(modified,"L","2026-10-26"))
    def test_paired_scoring(self):
        rows=[{"league":"L","date":"2026-10-22","home":"A","away":"B","market":"home_win",
               "method":m,"probability":p,"outcome":1} for m,p in (("TEAM_MODEL",.8),("LEAGUE_PRIOR",.5))]
        summary=paired_summary(rows,min_paired=1)
        self.assertEqual(summary[0]["n"],1)
        self.assertTrue(summary[0]["team_better_both"])
    def test_fallback_only(self):
        rows=[{"league":"L","date":"2026-10-22","home":"A","away":"B","market":"draw",
               "method":"LEAGUE_PRIOR","probability":.3,"outcome":0}]
        self.assertEqual(paired_summary(rows)[0]["cohort"],"FALLBACK_ONLY")
if __name__=="__main__":unittest.main()
