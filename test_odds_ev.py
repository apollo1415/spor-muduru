import unittest
from odds_ev import evaluate
class OddsTests(unittest.TestCase):
    def setUp(self):
        self.m=[{"league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-08T20:00:00+03:00","decision":"MODEL_ONLY_NO_ODDS","p_btts":".6"}]
        self.o=[{"league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-08T20:00:00+03:00","market":"btts","decimal_odds":"1.9","source":"verified","captured_at_utc":"2026-11-08T16:00:00Z"}]
    def test_ev(self):
        a,b=evaluate(self.m,self.o);self.assertEqual(len(a),1);self.assertEqual(a[0]["theoretical_ev"],.14)
    def test_missing_odds(self):
        a,b=evaluate(self.m,[]);self.assertEqual((len(a),len(b)),(0,0))
    def test_bad_price(self):
        self.o[0]["decimal_odds"]="1";self.assertEqual(len(evaluate(self.m,self.o)[1]),1)
    def test_after_kickoff(self):
        self.o[0]["captured_at_utc"]="2026-11-08T18:00:00Z";self.assertEqual(len(evaluate(self.m,self.o)[1]),1)
    def test_no_fuzzy_match(self):
        self.o[0]["home"]="Other";self.assertEqual(len(evaluate(self.m,self.o)[0]),0)
    def test_duplicates(self):
        self.assertEqual(len(evaluate(self.m,self.o*2)[1]),1)
if __name__=="__main__":unittest.main()
