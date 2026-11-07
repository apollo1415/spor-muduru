#!/usr/bin/env python3
"""Conservative market quality gate based on paired retrospective model comparison.
Research diagnostics only; never approves odds or publishes betting picks.
"""
import argparse,csv,json
from pathlib import Path

def assess(rows,min_paired=200):
    by_market={}
    for row in rows:
        if row.get("cohort")=="PAIRED":
            by_market.setdefault(row.get("market",""),[]).append(row)
    out=[]
    for market,items in sorted(by_market.items()):
        r=items[0]
        try:
            n=int(r["n"])
            tb=float(r["team_brier"]);pb=float(r["league_prior_brier"])
            tl=float(r["team_log_loss"]);pl=float(r["league_prior_log_loss"])
            valid=all(0<=v<=10 for v in (tb,pb,tl,pl))
        except (ValueError,TypeError,KeyError):
            n=0;valid=False
        if len(items)!=1:status="DUPLICATE_PAIRED_COHORT"
        elif not valid:status="INVALID_METRICS"
        elif n<min_paired:status="INSUFFICIENT_PAIRED_SAMPLE"
        elif tb<pb and tl<pl:status="TEAM_MODEL_RETROSPECTIVELY_BETTER"
        else:status="NO_CONSISTENT_TEAM_MODEL_ADVANTAGE"
        out.append({"market":market,"paired_n":n,"status":status,
                    "eligible_for_odds":"NO","deployment":"RESEARCH_ONLY"})
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="reports/model-comparison/comparison.csv")
    p.add_argument("--out",default="reports/model-comparison")
    a=p.parse_args()
    with open(a.input,encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    decisions=assess(rows)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with (out/"market_quality_gate.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["market","paired_n","status","eligible_for_odds","deployment"])
        w.writeheader();w.writerows(decisions)
    summary={"markets":decisions,"odds_approved":0,
             "warning":"Retrospective relative model comparison only; no calibration proof, forward validation, verified odds, or profitable betting evidence."}
    (out/"market_quality_gate.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"quality_gate":{x["market"]:x["status"] for x in decisions},"odds_approved":0},ensure_ascii=False))
if __name__=="__main__":main()
