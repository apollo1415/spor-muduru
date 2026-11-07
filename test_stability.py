import unittest
from stability import score_group
class StabilityTests(unittest.TestCase):
    def test_insufficient(self):
        self.assertEqual(score_group([])["status"],"INSUFFICIENT_SAMPLE")
    def test_date_separated(self):
        rows=[{"date":f"2026-01-{d:02d}","home":"A","away":"B","probability":".6","outcome":str(i%2)} for d in range(1,11) for i in range(10)]
        x=score_group(rows)
        self.assertEqual(x["status"],"AUDITED")
        self.assertEqual(x["early_n"],50)
        self.assertEqual(x["late_n"],50)
    def test_insufficient_dates(self):
        rows=[{"date":"2026-01-01","home":"A","away":"B","probability":".6","outcome":"1"} for i in range(60)]
        self.assertEqual(score_group(rows)["status"],"INSUFFICIENT_DATES")
if __name__=="__main__":unittest.main()
