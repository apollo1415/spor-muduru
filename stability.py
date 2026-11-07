#!/usr/bin/env python3
"""League/time stability audit. No odds or wagering recommendations."""
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
from backtest import metric

def score_group(rows,min_n=50):
    rows=sorted(rows,key=lambda r:(r["date"],r["home"],r["away"]))
    n=len(rows)
    if n<min_n:return {"status":"INSUFFICIENT_SAMPLE","n":n}
    dates=sorted(set(r["date"] for r in rows))
    if len(dates)<4:return {"status":"INSUFFICIENT_DATES","n":n}
    # Date-separated early/late evaluation: do not allow same-date crossover.
    midpoint=len(dates)//2
    first=[r for r in rows if r["date"]<dates[midpoint]]
    second=[r for r in rows if r["date"]>=dates[midpoint]]
    if min(len(first),len(second))<min_n//3:
        return {"status":"UNBALANCED_SPLIT","n":n,"early_n":len(first),"late_n":len(second)}
    def calc(part):
        data=[(float(r["probability"]),int(r["outcome"])) for r in part]
        observed=sum(y for _,y in data)/len(data)
        baseline=[(observed,y) for _,y in data]
        return {"model":metric(data),"constant_oracle_reference":metric(baseline)}
    early=calc(first);late=calc(second)
    # Constant-oracle reference uses the SAME evaluation outcomes; diagnostic only,
    # not a deployable baseline or a profitability comparison.
    return {"status":"AUDITED","n":n,"early_n":len(first),"late_n":len(second),
            "early":early,"late":late,"brier_change_late_minus_early":round(late["model"]["brier"]-early["model"]["brier"],5),
            "deployment":"RESEARCH_ONLY"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="reports/backtest/predictions.csv")
    ap.add_argument("--out",default="reports/stability")
    ap.add_argument("--min-n",type=int,default=50)
    args=ap.parse_args()
    with open(args.input,encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    groups=defaultdict(list)
    for r in rows:groups[(r["league"],r["market"])].append(r)
    report={f"{lg} | {market}":score_group(group,args.min_n) for (lg,market),group in sorted(groups.items())}
    counts=defaultdict(int)
    for x in report.values():counts[x["status"]]+=1
    output={"method":"league-by-market early/late chronological date-separated audit","min_group_n":args.min_n,
            "status_counts":dict(counts),"groups":report,
            "warning":"Retrospective revised data possible; no verified forward performance, odds or ROI. Oracle reference is NOT deployable. All markets RESEARCH_ONLY."}
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    (out/"summary.json").write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding="utf-8")
    with (out/"league_market_metrics.csv").open("w",newline="",encoding="utf-8-sig") as f:
        fields=["league","market","status","n","early_n","late_n","early_brier","late_brier","early_log_loss","late_log_loss","brier_change_late_minus_early"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for (lg,market),group in sorted(groups.items()):
            v=report[f"{lg} | {market}"]
            w.writerow({"league":lg,"market":market,"status":v["status"],"n":v["n"],
                        "early_n":v.get("early_n"),"late_n":v.get("late_n"),
                        "early_brier":v.get("early",{}).get("model",{}).get("brier"),
                        "late_brier":v.get("late",{}).get("model",{}).get("brier"),
                        "early_log_loss":v.get("early",{}).get("model",{}).get("log_loss"),
                        "late_log_loss":v.get("late",{}).get("model",{}).get("log_loss"),
                        "brier_change_late_minus_early":v.get("brier_change_late_minus_early")})
    print(json.dumps({"groups":len(groups),"status_counts":dict(counts)},ensure_ascii=False))
if __name__=="__main__":main()
