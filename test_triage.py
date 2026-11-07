import unittest
from triage import classify,build
class TriageTests(unittest.TestCase):
    def group(self,b=.2,l=.6,n=50):
        return {"status":"AUDITED","n":100,"late_n":n,
                "early":{"model":{"brier":.2,"log_loss":.6}},
                "late":{"model":{"brier":b,"log_loss":l}}}
    def test_deteriorating(self):
        self.assertEqual(classify(self.group(b=.24))[0],"DETERIORATING")
    def test_monitor(self):
        self.assertEqual(classify(self.group())[0],"MONITOR")
    def test_insufficient(self):
        self.assertEqual(classify(self.group(n=10))[0],"NO_EVIDENCE")
    def test_non_audited(self):
        self.assertEqual(classify({"status":"INSUFFICIENT_SAMPLE"})[0],"NO_EVIDENCE")
    def test_split_key(self):
        self.assertEqual(build({"England | League | btts":self.group()})[0]["league"],"England | League")
if __name__=="__main__":unittest.main()
