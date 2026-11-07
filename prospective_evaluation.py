#!/usr/bin/env python3
"""Score archived pre-match forecasts against completed fixtures; research only."""
import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from backtest import metric

MARKETS = {
    "home_win": ("p_home", lambda h, a: int(h > a)),
    "draw": ("p_draw", lambda h, a: int(h == a)),
    "away_win": ("p_away", lambda h, a: int(h < a)),
    "over25": ("p_over25", lambda h, a: int(h + a >= 3)),
    "btts": ("p_btts", lambda h, a: int(h > 0 and a > 0)),
}

def evaluate(snapshot, results, now):
    by_key = defaultdict(list)
    for r in results:
        by_key[(r.get("league"), r.get("home"), r.get("away"), r.get("date"))].append(r)
    scored = []
    skipped = defaultdict(int)
    seen = set()
    for f in snapshot.get("predictions", []):
        try:
            captured = datetime.fromisoformat(f["captured_at_utc"].replace("Z", "+00:00"))
            kickoff = datetime.fromisoformat(f["kickoff_istanbul"].replace("Z", "+00:00"))
            if captured.tzinfo is None or kickoff.tzinfo is None or captured >= kickoff:
                skipped["not_provably_prematch"] += 1
                continue
            if kickoff.astimezone(timezone.utc) >= now:
                skipped["not_started"] += 1
                continue
            # Source fixture date may differ from local kickoff date: use both calendar dates.
            dates = {kickoff.date().isoformat(), kickoff.astimezone(timezone.utc).date().isoformat()}
            matches = []
            for date in dates:
                matches.extend(by_key.get((f["league"], f["home"], f["away"], date), []))
            if len(matches) != 1:
                skipped["missing_or_ambiguous_result"] += 1
                continue
            match = matches[0]
            h, a = int(match["ft_home"]), int(match["ft_away"])
            if h < 0 or a < 0:
                raise ValueError("negative goals")
            key = (f["league"], f["home"], f["away"], kickoff.isoformat())
            if key in seen:
                skipped["duplicate_forecast"] += 1
                continue
            seen.add(key)
            for market, (field, outcome) in MARKETS.items():
                probability = float(f[field])
                if not 0 <= probability <= 1:
                    raise ValueError("invalid probability")
                scored.append({"league": f["league"], "home": f["home"], "away": f["away"],
                               "market": market, "probability": probability, "outcome": outcome(h, a),
                               "captured_at_utc": captured.isoformat()})
        except (KeyError, ValueError, TypeError, OverflowError):
            skipped["invalid_data"] += 1
    groups = defaultdict(list)
    leagues = defaultdict(list)
    for r in scored:
        pair = (r["probability"], r["outcome"])
        groups[r["market"]].append(pair)
        leagues[(r["league"], r["market"])].append(pair)
    return {"status": "RESEARCH_ONLY", "approved_for_betting": 0,
            "scored_market_rows": len(scored), "scored_matches": len(scored) // len(MARKETS),
            "skipped": dict(skipped), "markets": {k: metric(v) for k, v in sorted(groups.items())},
            "leagues": [{"league": lg, "market": market, **metric(v)}
                        for (lg, market), v in sorted(leagues.items())],
            "warning": "Fixture identity and kickoff timezone are not independently verified; historical source results may be revised. No ROI or betting approval."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshot", required=True)
    p.add_argument("--results", required=True, help="CSV containing league,date,home,away,ft_home,ft_away")
    p.add_argument("--out", default="reports/prospective/evaluation.json")
    a = p.parse_args()
    snapshot = json.loads(Path(a.snapshot).read_text(encoding="utf-8"))
    with open(a.results, encoding="utf-8-sig", newline="") as f:
        results = list(csv.DictReader(f))
    report = evaluate(snapshot, results, datetime.now(timezone.utc))
    path = Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"scored_matches": report["scored_matches"], "skipped": report["skipped"],
                      "approved_for_betting": 0}))

if __name__ == "__main__":
    main()
