import unittest
from calibration import fit_bins,apply_bins,audit
class CalibrationTests(unittest.TestCase):
    def test_empty_bins_preserve_probability(self):
        fit=fit_bins([(.15,0)]*10)
        self.assertEqual(apply_bins(.85,fit),.85)
    def test_fit_bounds(self):
        fit=fit_bins([(.7,1)]*100)
        self.assertTrue(0<=apply_bins(.7,fit)<=1)
    def test_date_separation(self):
        rows=[]
        for day in range(1,11):
            for j in range(20):
                rows.append({"date":f"2026-01-{day:02d}","league":"A","home":"H","away":"A","probability":".7","outcome":str(j%2)})
        result=audit(rows)
        self.assertEqual(result["status"],"EVALUATED")
        self.assertEqual(result["train_n"],120)
        self.assertEqual(result["test_n"],80)
        self.assertEqual(result["split_date"],"2026-01-07")
    def test_small_sample(self):
        self.assertEqual(audit([{"date":"2026-01-01"}])["status"],"INSUFFICIENT_DATES")
if __name__=="__main__":unittest.main()
