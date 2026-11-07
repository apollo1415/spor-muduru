#!/usr/bin/env python3
"""Walk-forward pre-match evaluation. Strictly prior calendar dates only.
Reports Brier/log loss/calibration; NOT ROI (no historical odds).
"""
import argparse,csv,json,math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from spor_muduru import get,csvrows,model

MARKETS={
    "home_win":("p_home",lambda r:float(r["ft_home"])>float(r["ft_away"])),
    "draw":("p_draw",lambda r:float(r["ft_home"])==float(r["ft_away"])),
    "away_win":("p_away",lambda r:float(r["ft_home"])<float(r["ft_away"])),
    "over25":("p_over25",lambda r:float(r["ft_home"])+float(r["ft_away"])>=3),
    "btts":("p_btts",lambda r:float(r["ft_home"])>0 and float(r["ft_away"])>0),
    "corners_over_9_5":("p_corners_over_9",lambda r:float(r["home_corners"])+float(r["away_corners"])>=10),
    "shots_over_23_5":("p_shots_over_23",lambda r:float(r["home_shots"])+float(r["away_shots"])>=24),
    "target_over_7_5":("p_target_over_7",lambda r:float(r["home_target"])+float(r["away_target"])>=8),
    "first_half_over_1_5":("p_first_half_goals_over_1",lambda r:float(r["ht_home"])+float(r["ht_away"])>=2),
    "first_half_corners_over_4_5":("p_first_half_corners_over_4",lambda r:float(r["home_corners_1h"])+float(r["away_corners_1h"])>=5)
}
FIELDS={
    "home_win":["ft_home","ft_away"],"draw":["ft_home","ft_away"],"away_win":["ft_home","ft_away"],
    "over25":["ft_home","ft_away"],"btts":["ft_home","ft_away"],
    "corners_over_9_5":["home_corners","away_corners"],
    "shots_over_23_5":["home_shots","away_shots"],
    "target_over_7_5":["home_target","away_target"],
    "first_half_over_1_5":["ht_home","ht_away"],
    "first_half_corners_over_4_5":["home_corners_1h","away_corners_1h"]
}
def metric(rows):
    n=len(rows)
    if not n:return {"n":0,"brier":None,"log_loss":None,"observed_rate":None,"mean_predicted":None,"calibration_gap":None}
    brier=sum((p-y)**2 for p,y in rows)/n
    logloss=-sum(y*math.log(max(1e-12,min(1-1e-12,p)))+(1-y)*math.log(max(1e-12,min(1-1e-12,1-p))) for p,y in rows)/n
    observed=sum(y for _,y in rows)/n;pred=sum(p for p,_ in rows)/n
    return {"n":n,"brier":round(brier,5),"log_loss":round(logloss,5),"observed_rate":round(observed,5),"mean_predicted":round(pred,5),"calibration_gap":round(pred-observed,5)}
def evaluate(results,league,asof,minimum_training=30):
    results=sorted(results,key=lambda r:(r.get("date",""),r.get("time","")))
    predictions=[];byday=defaultdict(list)
    for r in results:
        if r.get("date") and r["date"]<asof:byday[r["date"]].append(r)
    history=[]
    for day in sorted(byday):
        current=byday[day]
        if len(history)>=minimum_training:
            for r in current:
                if not r.get("home") or not r.get("away"):continue
                if any(r.get(k) in ("",None) for k in ("ft_home","ft_away")):continue
                z=model(r,history)
                if z.get("decision")!="MODEL_ONLY_NO_ODDS":continue
                for market,(key,outcome) in MARKETS.items():
                    if z.get(key) is None or any(r.get(f) in ("",None) for f in FIELDS[market]):continue
                    try:
                        predictions.append({"league":league,"date":day,"home":r["home"],"away":r["away"],"market":market,"probability":float(z[key]),"outcome":int(outcome(r)),"training_matches":len(history)})
                    except (ValueError,TypeError):continue
        history.extend(current)
    return predictions
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date",default=datetime.now().date().isoformat())
    ap.add_argument("--out",default="reports/backtest")
    ap.add_argument("--min-samples",type=int,default=30)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    import re
    leagues=list(dict.fromkeys(re.findall(r'^\|\s*`([^`]+)`\s*\|',get("LEAGUE_INDEX.md"),re.M)))
    allrows=[];failures=[]
    for lg in leagues:
        try:
            allrows.extend(evaluate(csvrows("data/"+lg+"/results_2627.csv"),lg,args.date))
        except Exception as e:failures.append({"league":lg,"error":str(e)[:150]})
    bymarket=defaultdict(list);bylg=defaultdict(list)
    for r in allrows:
        bymarket[r["market"]].append((r["probability"],r["outcome"]))
        bylg[(r["league"],r["market"])].append((r["probability"],r["outcome"]))
    summary={"asof_date_exclusive":args.date,"source":"open-matchday","method":"expanding window, strictly earlier dates, min 30 prior league results and 5 home/away matches","markets":{k:dict(metric(v),sufficient_sample=len(v)>=args.min_samples) for k,v in sorted(bymarket.items())},"leagues_attempted":len(leagues),"leagues_failed":failures,"predictions":len(allrows),"warning":"In-sample data source can be retrospectively revised. No timestamped historical odds; no ROI, profitability or verified forward performance. Uncalibrated model."}
    with (out/"predictions.csv").open("w",newline="",encoding="utf-8-sig") as f:
        fields=["league","date","home","away","market","probability","outcome","training_matches"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(allrows)
    with (out/"league_metrics.csv").open("w",newline="",encoding="utf-8-sig") as f:
        fields=["league","market","n","brier","log_loss","observed_rate","mean_predicted","calibration_gap"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for (lg,m),v in sorted(bylg.items()):w.writerow({"league":lg,"market":m,**metric(v)})
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"leagues_attempted":len(leagues),"failures":len(failures),"predictions":len(allrows),"markets":{k:v["n"] for k,v in summary["markets"].items()}},ensure_ascii=False))
    if not leagues or len(failures)==len(leagues):raise SystemExit(2)
if __name__=="__main__":main()
