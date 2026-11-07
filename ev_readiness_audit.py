#!/usr/bin/env python3
"""Cross-check retrospective calibration, quality gates and theoretical EV.
This is a diagnostic report only; it cannot approve odds or recommendations.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

def audit(calibration, quality, ev_rows):
    cal = calibration.get("markets", {})
    gate = {r["market"]: r for r in quality.get("markets", [])}
    counts = Counter(r.get("market", "") for r in ev_rows)
    markets = []
    for market in sorted(set(cal) | set(gate) | set(counts)):
        c = cal.get(market, {})
        g = gate.get(market, {})
        calibration_pass = c.get("status") == "EVALUATED" and c.get("improved_both_scores") is True
        retrospective_pass = g.get("status") == "TEAM_MODEL_RETROSPECTIVELY_BETTER"
        markets.append({
            "market": market,
            "ev_rows": counts[market],
            "calibration_status": c.get("status", "NOT_EVALUATED"),
            "calibration_improved_both": calibration_pass,
            "retrospective_quality_status": g.get("status", "NOT_EVALUATED"),
            "retrospective_quality_pass": retrospective_pass,
            "both_diagnostic_checks_pass": calibration_pass and retrospective_pass,
            "approved_for_betting": False,
            "reason": "No independent prospective validation, market-specific live-odds reliability or ROI evidence"
        })
    return {"status": "RESEARCH_ONLY", "markets": markets,
            "ev_rows_total": len(ev_rows), "approved_for_betting": 0,
            "warning": "Passing retrospective diagnostics is not betting approval."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--calibration", default="reports/calibration/summary.json")
    p.add_argument("--quality", default="reports/model-comparison/market_quality_gate.json")
    p.add_argument("--ev", default="reports/odds/research_ev.csv")
    p.add_argument("--out", default="reports/odds/ev_readiness_audit.json")
    a = p.parse_args()
    calibration = json.loads(Path(a.calibration).read_text(encoding="utf-8"))
    quality = json.loads(Path(a.quality).read_text(encoding="utf-8"))
    with open(a.ev, encoding="utf-8-sig", newline="") as f:
        ev_rows = list(csv.DictReader(f))
    result = audit(calibration, quality, ev_rows)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"status": result["status"], "ev_rows_total": result["ev_rows_total"],
                      "approved_for_betting": 0,
                      "diagnostic_pass_markets": [m["market"] for m in result["markets"]
                                                  if m["both_diagnostic_checks_pass"]]}))

if __name__ == "__main__":
    main()
