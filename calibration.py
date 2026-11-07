#!/usr/bin/env python3
"""Chronological out-of-sample calibration audit. Never train on evaluation dates."""
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from backtest import metric

def fit_bins(rows,bins=10,prior_strength=30):
    """Shrunken reliability bins. Prior is mean predicted probability in bin."""
    out=[]
    for i in range(bins):
        selected=[(p,y) for p,y in rows if min(bins-1,int(p*bins))==i]
        n=len(selected)
        if n:
            mean_p=sum(p for p,_ in selected)/n
            positives=sum(y for _,y in selected)
            calibrated=(positives+prior_strength*mean_p)/(n+prior_strength)
        else:
            calibrated=(i+.5)/bins
        out.append({"bin":i,"n":n,"value":calibrated})
    return out

def apply_bins(p,fit):
    idx=min(len(fit)-1,max(0,int(p*len(fit))))
    # Unseen bins preserve original probability rather than fabricate evidence.
    return fit[idx]["value"] if fit[idx]["n"] else p

def audit(rows,train_fraction=.6,min_train=100,min_test=50):
    """Split by distinct date: same-day events never cross the split."""
    rows=sorted(rows,key=lambda r:(r.get("date",""),r.get("league",""),r.get("home",""),r.get("away","")))
    days=sorted({r["date"] for r in rows})
    if len(days)<2:return {"status":"INSUFFICIENT_DATES","n":len(rows)}
    cut=max(1,min(len(days)-1,int(len(days)*train_fraction)))
    train=[r for r in rows if r["date"]<days[cut]]
    test=[r for r in rows if r["date"]>=days[cut]]
    if len(train)<min_train or len(test)<min_test:
        return {"status":"INSUFFICIENT_SAMPLE","train_n":len(train),"test_n":len(test),"split_date":days[cut]}
    fit=fit_bins([(float(r["probability"]),int(r["outcome"])) for r in train])
    raw=[(float(r["probability"]),int(r["outcome"])) for r in test]
    adjusted=[(apply_bins(p,fit),y) for p,y in raw]
    base=metric(raw);cal=metric(adjusted)
    # No promotion without independent improvement in BOTH proper scoring rules.
    eligible=cal["brier"]<base["brier"] and cal["log_loss"]<base["log_loss"]
    return {"status":"EVALUATED","train_n":len(train),"test_n":len(test),
            "split_date":days[cut],"baseline":base,"calibrated":cal,
            "improved_both_scores":eligible,"deployment":"RESEARCH_ONLY",
            "fit_bins":fit}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="reports/backtest/predictions.csv")
    ap.add_argument("--out",default="reports/calibration")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    with open(args.input,encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    groups=defaultdict(list)
    for r in rows:groups[r["market"]].append(r)
    reports={k:audit(v) for k,v in sorted(groups.items())}
    summary={"method":"chronological date-separated 60% train / 40% test; 10-bin shrinkage; no same-day leakage",
             "markets":reports,"warning":"Retrospective audit only; no prospective validation, odds or ROI. All models RESEARCH_ONLY."}
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    with (out/"market_metrics.csv").open("w",encoding="utf-8-sig",newline="") as f:
        fields=["market","status","train_n","test_n","split_date","baseline_brier","calibrated_brier","baseline_log_loss","calibrated_log_loss","improved_both_scores","deployment"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for k,v in reports.items():
            w.writerow({"market":k,"status":v["status"],"train_n":v.get("train_n"),"test_n":v.get("test_n"),
                        "split_date":v.get("split_date"),"baseline_brier":v.get("baseline",{}).get("brier"),
                        "calibrated_brier":v.get("calibrated",{}).get("brier"),
                        "baseline_log_loss":v.get("baseline",{}).get("log_loss"),
                        "calibrated_log_loss":v.get("calibrated",{}).get("log_loss"),
                        "improved_both_scores":v.get("improved_both_scores"),"deployment":v.get("deployment","NOT_ELIGIBLE")})
    print(json.dumps({"markets":{k:{"status":v["status"],"train_n":v.get("train_n"),"test_n":v.get("test_n"),"improved_both_scores":v.get("improved_both_scores")} for k,v in reports.items()}},ensure_ascii=False))
if __name__=="__main__":main()
