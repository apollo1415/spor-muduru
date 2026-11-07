import unittest
from fixture_review import review
class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.f=[{"league":"L","home":"Alpha","away":"Beta","kickoff_istanbul":"2026-11-10T20:00:00+03:00"}]
        self.e=[{"id":"e","sport_key":"soccer_test","home_team":"Alpha","away_team":"Beta","commence_time":"2026-11-10T17:00:00Z"}]
    def test_unique_requires_review(self):
        r=review(self.f,self.e);self.assertEqual(len(r),1);self.assertEqual(r[0]["approved"],"NO");self.assertEqual(r[0]["review_status"],"REVIEW_TIME_AND_LEAGUE")
    def test_ambiguous(self):
        self.e.append(dict(self.e[0],id="e2"));r=review(self.f,self.e);self.assertEqual(len(r),2);self.assertTrue(all(x["review_status"]=="AMBIGUOUS_MULTIPLE_PAIRS" for x in r))
    def test_timezone_warning(self):
        self.e[0]["commence_time"]="2026-11-10T18:00:00Z"
        self.assertEqual(review(self.f,self.e)[0]["time_review"],"SOURCE_TIMEZONE_UNVERIFIED")
    def test_near_time_still_unverified(self):
        self.assertEqual(review(self.f,self.e)[0]["time_review"],"TIME_WITHIN_30M_UNVERIFIED")
    def test_other_team(self):
        self.e[0]["away_team"]="Other";self.assertEqual(review(self.f,self.e),[])
    def test_time_too_far(self):
        self.e[0]["commence_time"]="2026-11-12T17:00:00Z";self.assertEqual(review(self.f,self.e),[])
if __name__=="__main__":unittest.main()
