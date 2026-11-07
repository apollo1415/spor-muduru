import unittest
from count_models import poisson_tail,estimate_total
class CountTests(unittest.TestCase):
    def test_zero(self):
        self.assertAlmostEqual(poisson_tail(0,0),0)
    def test_tail(self):
        self.assertAlmostEqual(poisson_tail(2,0),1-__import__("math").exp(-2))
    def test_insufficient(self):
        self.assertIsNone(estimate_total([1],[2],[3],[4]))
    def test_average(self):
        self.assertEqual(estimate_total([2]*5,[1]*5,[3]*5,[4]*5),5)
if __name__=="__main__":unittest.main()
