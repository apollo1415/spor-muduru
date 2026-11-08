import unittest
from datetime import datetime, timezone

from odds_discovery import candidates, daily_inventory, event_url, provider_sports, soccer_sports


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.matches = [{"league": "L", "home": "Alpha FC", "away": "Beta",
                         "kickoff_istanbul": "2026-11-09T20:00:00+03:00",
                         "decision": "MODEL_ONLY_NO_ODDS"}]
        self.events = [{"id": "x", "sport_key": "soccer_test", "home_team": "Alpha FC",
                        "away_team": "Beta", "commence_time": "2026-11-09T17:00:00Z"}]

    def test_candidate_not_approved(self):
        result = candidates(self.matches, self.events, "soccer_test")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "REVIEW_REQUIRED_NOT_APPROVED")

    def test_wrong_date(self):
        self.events[0]["commence_time"] = "2026-11-10T17:00:00Z"
        self.assertEqual(candidates(self.matches, self.events, "soccer_test"), [])

    def test_wrong_team(self):
        self.events[0]["away_team"] = "Gamma"
        self.assertEqual(candidates(self.matches, self.events, "soccer_test"), [])

    def test_started_excluded(self):
        self.matches[0]["decision"] = "STARTED_OR_PAST"
        self.assertEqual(candidates(self.matches, self.events, "soccer_test"), [])

    def test_active_soccer_sports_are_discovered(self):
        sports = [
            {"key": "soccer_b", "group": "Soccer", "active": True},
            {"key": "basketball_a", "group": "Basketball", "active": True},
            {"key": "soccer_a", "group": "Soccer", "active": True},
            {"key": "soccer_old", "group": "Soccer", "active": False},
        ]
        self.assertEqual(soccer_sports(sports), ["soccer_a", "soccer_b"])

    def test_explicit_sports_override_skips_provider_listing(self):
        def must_not_run(_):
            raise AssertionError("loader should not run")
        sports, source = provider_sports("secret", "soccer_epl,soccer_epl,soccer_spain_la_liga", must_not_run)
        self.assertEqual(sports, ["soccer_epl", "soccer_spain_la_liga"])
        self.assertEqual(source, "EXPLICIT")

    def test_event_endpoint_has_time_window_and_no_odds_query(self):
        start = datetime(2026, 11, 8, tzinfo=timezone.utc)
        end = datetime(2026, 11, 22, tzinfo=timezone.utc)
        url = event_url("soccer_epl", "secret", start, end)
        self.assertIn("/events?", url)
        self.assertNotIn("/odds?", url)
        self.assertIn("commenceTimeFrom=2026-11-08T00%3A00%3A00Z", url)

    def test_daily_inventory_is_separate_and_unverified(self):
        rows = daily_inventory(self.events + [self.events[0]], "2026-11-09")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "UNVERIFIED_PROVIDER_FIXTURE")
        self.assertEqual(rows[0]["official_fixture_verified"], "NO")
        self.assertEqual(rows[0]["real_odds_verified"], "NO")
        self.assertEqual(rows[0]["ev_verified"], "NO")

    def test_daily_inventory_filters_istanbul_calendar_date(self):
        event = [{"id": "late", "sport_key": "soccer_test", "home_team": "A", "away_team": "B",
                  "commence_time": "2026-11-08T22:30:00Z"}]
        self.assertEqual(len(daily_inventory(event, "2026-11-09")), 1)
        self.assertEqual(daily_inventory(event, "2026-11-08"), [])


if __name__ == "__main__":
    unittest.main()
