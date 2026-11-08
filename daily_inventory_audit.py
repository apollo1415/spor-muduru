#!/usr/bin/env python3
"""Audit daily fixture coverage without treating missing data as successful coverage."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def audit(report_dir):
    report_dir = Path(report_dir)
    matches = read_csv(report_dir / "matches.csv")
    coverage = read_csv(report_dir / "coverage.csv")
    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    decisions = Counter(row.get("decision") or "UNCLASSIFIED" for row in matches)
    league_counts = Counter(row.get("league") or "UNKNOWN" for row in matches)
    source_errors = [row["league"] for row in coverage if row.get("status") != "OK"]
    modelled = decisions.get("MODEL_ONLY_NO_ODDS", 0)
    eligible = sum(n for status, n in decisions.items()
                   if status not in ("STARTED_OR_PAST", "UNKNOWN_KICKOFF"))
    result = {
        "date": summary.get("date"),
        "source": summary.get("source"),
        "source_is_official_iddaa": False,
        "leagues_attempted": len(coverage),
        "leagues_ok": len(coverage) - len(source_errors),
        "leagues_failed": len(source_errors),
        "failed_leagues": source_errors,
        "source_fixtures_today": len(matches),
        "future_or_unresolved_fixtures": eligible,
        "modelled_fixtures": modelled,
        "not_modelled_future_fixtures": max(0, eligible - modelled),
        "decisions": dict(sorted(decisions.items())),
        "matches_by_league": dict(sorted(league_counts.items())),
        "official_fixture_verified": False,
        "real_odds_verified": False,
        "ev_verified": False,
        "limitations": [
            "Only source-listed fixtures are counted; missing official coupon matches cannot be inferred.",
            "Fixture identity, real odds and EV require independent evidence.",
            "Successful workflow execution is not proof of complete match coverage."
        ],
    }
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", default="reports/today")
    args = parser.parse_args()
    directory = Path(args.report_dir)
    result = audit(directory)
    (directory / "inventory_audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
if __name__ == "__main__":
    main()
