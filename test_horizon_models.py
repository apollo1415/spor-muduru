import unittest
from datetime import datetime,timezone
from horizon_models import build

class HorizonModelTests(unittest.TestCase):
    def test_future_fixture_with_history(self):
        fixtures=[{"league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-10T20:00:00+03:00"}]
        history=[]
        for i in range(7):
            history.append({"date":"2026-10-%02d"%(i+1),"home":"A","away":"B","ft_home":"2","ft_away":"1"})
        result=build(fixtures,{"L":history},datetime(2026,11,7,tzinfo=timezone.utc))
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["decision"],"MODEL_ONLY_NO_ODDS")
        self.assertEqual(result[0]["source_timezone_unverified"],"YES")
    def test_no_future_history_leakage(self):
        fixtures=[{"league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-10T20:00:00+03:00"}]
        future=[{"date":"2026-11-09","home":"A","away":"B","ft_home":"2","ft_away":"1"} for _ in range(7)]
        result=build(fixtures,{"L":future},datetime(2026,11,7,tzinfo=timezone.utc))
        self.assertEqual(result[0]["decision"],"INSUFFICIENT_HISTORY")
    def test_past_fixture_skipped(self):
        fixtures=[{"league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-06T20:00:00+03:00"}]
        self.assertEqual(build(fixtures,{},datetime(2026,11,7,tzinfo=timezone.utc)),[])
if __name__=="__main__":unittest.main()
