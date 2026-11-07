import unittest
from odds_provider import transform,group_mappings
class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.event={"id":"e1","home_team":"Alpha","away_team":"Beta","commence_time":"2026-11-09T17:00:00Z",
                    "bookmakers":[{"key":"book1","last_update":"2026-11-09T12:00:00Z",
                      "markets":[{"key":"h2h","outcomes":[{"name":"Alpha","price":2.1},{"name":"Draw","price":3.1},{"name":"Beta","price":3.6}]},
                                 {"key":"totals","outcomes":[{"name":"Over","point":2.5,"price":1.9}]}]}]}
        self.mapping={"e1":{"provider_home":"Alpha","provider_away":"Beta","league":"L","home":"A","away":"B","kickoff_istanbul":"2026-11-09T20:00:00+03:00"}}
    def test_multi_league_groups(self):
        maps=[
            {"event_id":"e1","league":"ENG_1_premier-league"},
            {"event_id":"e2","league":"TUR_1_super-lig"}]
        groups=group_mappings(maps)
        self.assertEqual(set(groups),{"soccer_epl","soccer_turkey_super_league"})
        self.assertIn("e2",groups["soccer_turkey_super_league"])
    def test_unsupported_league_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"UNSUPPORTED_LEAGUE_MAPPING"):
            group_mappings([{"event_id":"e3","league":"UNKNOWN"}])
    def test_four_markets(self):
        rows,errors=transform([self.event],self.mapping,"2026-11-09T13:00:00Z")
        self.assertEqual(len(rows),4);self.assertEqual(errors,[])
    def test_duplicate_bookmaker_quotes_choose_latest(self):
        import copy
        other=copy.deepcopy(self.event["bookmakers"][0]);other["key"]="book2"
        other["last_update"]="2026-11-09T12:30:00Z"
        other["markets"][0]["outcomes"][0]["price"]=2.4
        self.event["bookmakers"].append(other)
        rows,errors=transform([self.event],self.mapping,"2026-11-09T13:00:00Z")
        self.assertEqual(len(rows),4)
        self.assertEqual([r for r in rows if r["market"]=="home_win"][0]["decimal_odds"],2.4)
        self.assertEqual(errors,[])
    def test_unmapped_is_skipped(self):
        self.assertEqual(transform([self.event],{},"2026-11-09T13:00:00Z")[0],[])
    def test_wrong_team_rejected(self):
        self.mapping["e1"]["provider_home"]="Wrong"
        self.assertEqual(len(transform([self.event],self.mapping,"2026-11-09T13:00:00Z")[1]),1)
    def test_wrong_kickoff_rejected(self):
        self.mapping["e1"]["kickoff_istanbul"]="2026-11-09T21:00:00+03:00"
        self.assertEqual(len(transform([self.event],self.mapping,"2026-11-09T13:00:00Z")[0]),0)
    def test_stale_after_start(self):
        self.event["bookmakers"][0]["last_update"]="2026-11-09T18:00:00Z"
        self.assertEqual(len(transform([self.event],self.mapping,"2026-11-09T19:00:00Z")[0]),0)
if __name__=="__main__":unittest.main()
