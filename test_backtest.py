import math,unittest
from backtest import metric,evaluate
class BacktestTests(unittest.TestCase):
    def test_perfect(self):
        x=metric([(1.,1),(0.,0)])
        self.assertAlmostEqual(x["brier"],0.)
        self.assertLess(x["log_loss"],1e-6)
    def test_calibration(self):
        x=metric([(.8,1),(.8,0)])
        self.assertAlmostEqual(x["calibration_gap"],.3)
    def test_no_future_leakage(self):
        # Insufficient training data: no predictions, regardless of future rows.
        data=[{"date":"2026-01-01","home":"A","away":"B","ft_home":"1","ft_away":"0"}]
        self.assertEqual(evaluate(data,"TEST","2026-02-01"),[])
    def test_no_after_cutoff(self):
        data=[{"date":"2026-12-01","home":"A","away":"B","ft_home":"1","ft_away":"0"}]
        self.assertEqual(evaluate(data,"TEST","2026-11-01"),[])
if __name__=="__main__":unittest.main()
