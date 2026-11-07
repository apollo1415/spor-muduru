#!/usr/bin/env python3
"""Freeze pre-kickoff research forecasts as timestamped CI artifacts, never betting picks."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("p_home", "p_draw", "p_away", "p_over25", "p_btts")

def freeze(rows, now):
    frozen = []
    for r in rows:
        if r.get("decision") != "MODEL_ONLY_NO_ODDS":
            continue
        try:
            kickoff = datetime.fromisoformat(r["kickoff_istanbul"].replace("Z", "+00:00"))
            if kickoff.tzinfo is None or kickoff.astimezone(timezone.utc) <= now:
                continue
            probs = {key: float(r[key]) for key in FIELDS}
            if any(not 0 <= v <= 1 for v in probs.values()):
                continue
            if abs(probs["p_home"] + probs["p_draw"] + probs["p_away"] - 1) > .005:
                continue
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        frozen.append({
            "league": r["league"], "home": r["home"], "away": r["away"],
            "kickoff_istanbul": r["kickoff_istanbul"],
            "captured_at_utc": now.isoformat(),
            "source_timezone_unverified": r.get("source_timezone_unverified", "YES"),
            "decision": "RESEARCH_ONLY_PREMATCH_SNAPSHOT", **probs,
        })
    return frozen

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="reports/horizon/matches.csv")
    parser.add_argument("--out", default="reports/forward-snapshots")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze(rows, now)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    path = out / ("predictions_" + stamp + ".json")
    path.write_text(json.dumps({
        "captured_at_utc": now.isoformat(), "predictions": frozen,
        "status": "RESEARCH_ONLY", "approved_for_betting": 0,
        "warning": "Immutable per-run artifact only; no persistent longitudinal store or automated result matching yet. Fixture identity/timezone unverified."
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"snapshot_file": path.name, "predictions": len(frozen), "approved_for_betting": 0}))

if __name__ == "__main__":
    main()
