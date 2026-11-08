import unittest
from datetime import datetime, timezone

from full_fixture_report import build_rows, make_row, probability_triplet

NOW = datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)
DAY = "2026-11-09"


def fixture(**extras):
    result = {
        "league": "L1",
        "home": "Alpha",
        "away": "Beta",
        "kickoff_istanbul": "2026-11-09T20:00:00+03:00",
        "decision": "INSUFFICIENT_HISTORY",
    }
    result.update(extras)
    return result


class FullFixtureResearchTests(unittest.TestCase):
    def test_valid_model_keeps_confidence_separate_from_accuracy(self):
        f = fixture(decision="MODEL_ONLY_NO_ODDS", p_home=".612",
                    p_draw=".221", p_away=".167", p_over25=".55",
                    p_btts=".48", n_home="7", n_away="6")
        row = make_row(f, DAY, NOW, "KAYNAK")
        self.assertEqual(row["MS tahmini"], "1")
        self.assertEqual(row["Güven %"], 61.2)
        self.assertEqual(row["Model turu"], "TAKIM_POISSON_DENEYSEL")
        self.assertEqual(row["Kalibrasyon"], "DOGRULANMADI")
        self.assertEqual(row["2.5 Ust %"], 55.0)
        self.assertEqual(row["Resmi Iddaa"], "DOGRULANMADI")

    def test_invalid_probabilities_do_not_generate_forecast(self):
        for triplet in ((.6, .4, .3), (.7, -.1, .4),
                        ("nan", .2, .8), ("not-a-number", .2, .8)):
            row = fixture(decision="MODEL_ONLY_NO_ODDS",
                          p_home=triplet[0], p_draw=triplet[1],
                          p_away=triplet[2])
            self.assertIsNone(probability_triplet(row))
            produced = make_row(row, DAY, NOW, "KAYNAK")
            self.assertEqual(produced["MS tahmini"], "")
            self.assertEqual(produced["Güven %"], "")

    def test_provider_without_review_remains_visible_with_blank_probability(self):
        provider = [{"event_id": "E1", "provider_sport": "soccer_league",
                     "home": "Gamma", "away": "Delta",
                     "kickoff_istanbul": "2026-11-09T22:00:00+03:00"}]
        rows, summary = build_rows([], [], provider, [], [], DAY, NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Kaynak"], "PROVIDER")
        self.assertEqual(rows[0]["Güven %"], "")
        self.assertEqual(summary["official_iddaa_bulletin_count"], None)
        self.assertFalse(summary["cross_source_identity_deduplicated"])

    def test_review_probabilities_are_not_falsely_approved(self):
        p = {"event_id": "E1", "home": "Gamma", "away": "Delta",
             "kickoff_istanbul": "2026-11-09T22:00:00+03:00"}
        review = {"event_id": "E1", "research_model": "STANDARD_RESEARCH",
                  "p_home": ".5", "p_draw": ".3", "p_away": ".2"}
        rows, summary = build_rows([], [], [p], [], [review], DAY, NOW)
        self.assertEqual(rows[0]["MS tahmini"], "1")
        self.assertEqual(rows[0]["Güven %"], 50.0)
        self.assertIn("ONAYSIZ", rows[0]["Model turu"])
        self.assertEqual(rows[0]["Kimlik kontrolu"], "PROVIDER_BAGLANTISI_ONAYSIZ")
        self.assertEqual(summary["provider_review_probabilities"], 1)
        self.assertEqual(summary["odds_approved"], 0)

    def test_source_and_horizon_dedupe_exact_identity_only(self):
        basic = fixture()
        model = fixture(decision="MODEL_ONLY_NO_ODDS", p_home=".55",
                        p_draw=".25", p_away=".20")
        rows, summary = build_rows([basic], [model], [], [], [], DAY, NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["MS tahmini"], "1")
        self.assertEqual(summary["source_rows_unique_by_exact_identity"], 1)

    def test_prior_explicitly_marked_not_team_specific(self):
        missing = fixture()
        fallback = fixture(baseline_status="LEAGUE_PRIOR_RESEARCH_ONLY",
                           p_home=".42", p_draw=".30", p_away=".28",
                           league_sample="32")
        rows, summary = build_rows([missing], [], [], [fallback], [], DAY, NOW)
        self.assertEqual(rows[0]["Model turu"], "LIG_ORTALAMASI_TAKIMA_OZEL_DEGIL")
        self.assertEqual(rows[0]["Güven %"], 42.0)
        self.assertEqual(summary["rows_with_experimental_1x2"], 1)

    def test_started_and_wrong_date_have_no_future_forecast(self):
        old = fixture(kickoff_istanbul="2026-11-09T10:00:00+03:00",
                      decision="MODEL_ONLY_NO_ODDS", p_home=".5",
                      p_draw=".3", p_away=".2")
        row = make_row(old, DAY, NOW, "KAYNAK")
        self.assertEqual(row["Mac durumu"], "BASLADI")
        self.assertEqual(row["MS tahmini"], "")
        another_day = fixture(kickoff_istanbul="2026-11-10T20:00:00+03:00")
        self.assertIsNone(make_row(another_day, DAY, NOW, "KAYNAK"))

    def test_different_sources_preserve_overlap_until_verified(self):
        f = fixture()
        provider = {"event_id": "E2", "home": "Alpha", "away": "Beta",
                    "kickoff_istanbul": f["kickoff_istanbul"]}
        rows, summary = build_rows([f], [], [provider], [], [], DAY, NOW)
        self.assertEqual(len(rows), 2)
        self.assertEqual(summary["provider_rows_unverified"], 1)
        self.assertIsNone(summary["official_bulletin_coverage_percent"])

    def test_duplicate_provider_event_is_suppressed(self):
        p = {"event_id": "E1", "home": "Gamma", "away": "Delta",
             "kickoff_istanbul": "2026-11-09T22:00:00+03:00"}
        rows, summary = build_rows([], [], [p, p], [], [], DAY, NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(summary["provider_rows_unverified"], 1)

    def test_missing_source_time_keeps_row_if_day_known(self):
        f = fixture(kickoff_istanbul="", source_date=DAY,
                    decision="MODEL_ONLY_NO_ODDS", p_home=".5",
                    p_draw=".3", p_away=".2")
        row = make_row(f, DAY, NOW, "KAYNAK")
        self.assertEqual(row["Mac durumu"], "SAAT_DOGRULANAMADI")
        self.assertEqual(row["MS tahmini"], "")


if __name__ == "__main__":
    unittest.main()
