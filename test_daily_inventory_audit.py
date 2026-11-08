import csv
import json
import tempfile
import unittest
from pathlib import Path

from daily_inventory_audit import audit


def write_csv(path, rows):
    fields = sorted(set().union(*(row.keys() for row in rows)))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class DailyInventoryAuditTests(unittest.TestCase):
    def make_report(self, include_provider):
        temporary = tempfile.TemporaryDirectory()
        report = Path(temporary.name)
        write_csv(report / "matches.csv", [
            {"league": "L", "decision": "MODEL_ONLY_NO_ODDS"},
            {"league": "L", "decision": "INSUFFICIENT_HISTORY"},
        ])
        write_csv(report / "coverage.csv", [{"league": "L", "status": "OK"}])
        (report / "summary.json").write_text(json.dumps({"date": "2026-11-09", "source": "test"}))
        if include_provider:
            write_csv(report / "provider_fixture_inventory.csv", [
                {"event_id": "one", "status": "UNVERIFIED_PROVIDER_FIXTURE"},
                {"event_id": "two", "status": "UNVERIFIED_PROVIDER_FIXTURE"},
                {"event_id": "three", "status": "UNVERIFIED_PROVIDER_FIXTURE"},
            ])
        return temporary, report

    def test_reports_provider_inventory_separately(self):
        temporary, report = self.make_report(True)
        self.addCleanup(temporary.cleanup)
        result = audit(report)
        self.assertEqual(result["source_fixtures_today"], 2)
        self.assertEqual(result["provider_fixtures_today_unverified"], 3)
        self.assertEqual(result["visible_fixture_rows_not_deduplicated"], 5)
        self.assertTrue(result["provider_inventory_present"])
        self.assertFalse(result["official_fixture_verified"])

    def test_missing_provider_inventory_is_explicit(self):
        temporary, report = self.make_report(False)
        self.addCleanup(temporary.cleanup)
        result = audit(report)
        self.assertEqual(result["provider_fixtures_today_unverified"], 0)
        self.assertFalse(result["provider_inventory_present"])


if __name__ == "__main__":
    unittest.main()
