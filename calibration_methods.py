#!/usr/bin/env python3
"""Chronological three-way calibration benchmark; diagnostic, never odds approval."""
import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from backtest import metric
from calibration import fit_bins, apply_bins

def benchmark(rows, min_fit=100, min_validation=50, min_holdout=50):
    rows = sorted(rows, key=lambda r: (r["date"], r.get("league", ""), r.get("home", ""), r.get("away", "")))
    dates = sorted({r["date"] for r in rows})
    if len(dates) < 5:
        return {"status": "INSUFFICIENT_DATES"}
    first = dates[int(len(dates) * .5)]
    second = dates[int(len(dates) * .75)]
    fit = [r for r in rows if r["date"] < first]
    validation = [r for r in rows if first <= r["date"] < second]
    holdout = [r for r in rows if r["date"] >= second]
    if len(fit) < min_fit or len(validation) < min_validation or len(holdout) < min_holdout:
        return {"status": "INSUFFICIENT_SAMPLE", "fit_n": len(fit), "validation_n": len(validation), "holdout_n": len(holdout)}
    training = [(float(r["probability"]), int(r["outcome"])) for r in fit]
    val = [(float(r["probability"]), int(r["outcome"])) for r in validation]
    test = [(float(r["probability"]), int(r["outcome"])) for r in holdout]
    if any(not math.isfinite(p) or not 0 <= p <= 1 or y not in (0, 1) for sample in (training, val, test) for p, y in sample):
        return {"status": "INVALID_PROBABILITIES"}
    bins = fit_bins(training)
    rate = sum(y for _, y in training) / len(training)
    methods = {
        "identity": lambda p: p,
        "shrink_25": lambda p: .75 * p + .25 * rate,
        "shrink_50": lambda p: .5 * p + .5 * rate,
        "shrink_75": lambda p: .25 * p + .75 * rate,
        "ten_bin_shrinkage": lambda p: apply_bins(p, bins),
    }
    def scored(data, fn):
        return metric([(min(1., max(0., fn(p))), y) for p, y in data])
    scores = {name: scored(val, fn) for name, fn in methods.items()}
    # Select exclusively on validation Brier; tie-break by log loss then name.
    chosen = min(methods, key=lambda name: (scores[name]["brier"], scores[name]["log_loss"], name))
    base = scored(test, methods["identity"])
    result = scored(test, methods[chosen])
    # Freeze the method before holdout; report chronological stability without reselection.
    holdout_days = sorted({r["date"] for r in holdout})
    if len(holdout_days) >= 2:
        midpoint = holdout_days[len(holdout_days) // 2]
        segments = [
            ("early", [r for r in holdout if r["date"] < midpoint]),
            ("late", [r for r in holdout if r["date"] >= midpoint]),
        ]
    else:
        segments = []
    stability = []
    for name, segment in segments:
        pairs = [(float(r["probability"]), int(r["outcome"])) for r in segment]
        baseline = scored(pairs, methods["identity"])
        adjusted = scored(pairs, methods[chosen])
        stability.append({
            "segment": name, "n": len(pairs), "status": "EVALUATED" if len(pairs) >= 30 else "INSUFFICIENT_SAMPLE",
            "baseline": baseline, "selected": adjusted,
            "improved_both": (adjusted["brier"] < baseline["brier"] and
                              adjusted["log_loss"] < baseline["log_loss"]) if len(pairs) >= 30 else None,
        })
    stable_both_halves = (len(stability) == 2 and
                          all(x["improved_both"] is True for x in stability))
    return {"status": "EVALUATED", "fit_n": len(fit), "validation_n": len(val),
            "holdout_n": len(test), "validation_start": first, "holdout_start": second,
            "selected_on_validation": chosen, "validation_scores": scores,
            "holdout_baseline": base, "holdout_selected": result,
            "holdout_improved_both": result["brier"] < base["brier"] and result["log_loss"] < base["log_loss"],
            "holdout_segments": stability, "stable_both_halves": stable_both_halves,
            "deployment": "RESEARCH_ONLY"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="reports/backtest/predictions.csv")
    p.add_argument("--out", default="reports/calibration/method_comparison.json")
    a = p.parse_args()
    with open(a.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    groups = defaultdict(list)
    for row in rows:
        groups[row["market"]].append(row)
    results = {market: benchmark(group) for market, group in sorted(groups.items())}
    output = {"method": "Date-separated 50% fit / 25% validation / 25% untouched holdout; choose on validation only",
              "markets": results, "approved_for_betting": 0, "deployment": "RESEARCH_ONLY",
              "warning": "Retrospective and potentially revised source data; no prospective or odds-based validation."}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"markets": {k: {"status": v["status"], "selected": v.get("selected_on_validation"),
                                      "holdout_improved_both": v.get("holdout_improved_both"),
                                      "stable_both_halves": v.get("stable_both_halves")} for k, v in results.items()},
                      "approved_for_betting": 0}))

if __name__ == "__main__":
    main()
