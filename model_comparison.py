#!/usr/bin/env python3
"""Chronological paired comparison of team model and league-only prior. Research only."""
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path
from spor_muduru import get,csvrows,model,poisson,value
from league_prior_fallback import prior
from backtest import metric

MARKETS={"home_win":("p_home",lambda h,a:int(h>a)),"draw":("p_draw",lambda h,a:int(h==a)),
         "away_win":("p_away",lambda h,a:int(h<a)),"over25":("p_over25",lambda h,a:int(h+a>=3)),
         "btts":("p_btts",lambda h,a:int(h>0 and a>0))}
def evaluate_pair(results,league,asof):
    byday=defaultdict(list)
    for r in results:
        if r.get("date") and r["date"]<asof:byday[r["date"]].append(r)
    history=[];out=[]
    for day in sorted(byday):
        current=byday[day]
        p=prior(history,day)
        for r in current:
            h=value(r.get("ft_home"));a=value(r.get("ft_away"))
            if h is None or a is None or h<0 or a<0 or not r.get("home") or not r.get("away"):continue
            standard=model(r,history) if p else {}
            baseline=poisson(max(.15,min(5,p[0])),max(.15,min(5,p[1]))) if p else {}
            for name,(key,outcome) in MARKETS.items():
                if not p:continue
                for method,prob in (("LEAGUE_PRIOR",baseline.get(key)),("TEAM_MODEL",standard.get(key))):
                    if prob is None:continue
                    out.append({"league":league,"date":day,"home":r["home"],"away":r["away"],"market":name,
                                "method":method,"probability":float(prob),"outcome":outcome(h,a),
                                "team_model_available":standard.get("decision")=="MODEL_ONLY_NO_ODDS"})
        history.extend(current)
    return out

def paired_summary(rows,min_paired=30):
    keys=defaultdict(dict)
    for r in rows:
        k=(r["league"],r["date"],r["home"],r["away"],r["market"])
        keys[k][r["method"]]=(float(r["probability"]),int(r["outcome"]))
    groups=defaultdict(lambda:defaultdict(list))
    for k,v in keys.items():
        if "LEAGUE_PRIOR" not in v:continue
        group=k[4]
        if "TEAM_MODEL" in v:
            for method in ("LEAGUE_PRIOR","TEAM_MODEL"):groups[(group,"PAIRED")][method].append(v[method])
        else:groups[(group,"FALLBACK_ONLY")]["LEAGUE_PRIOR"].append(v["LEAGUE_PRIOR"])
    out=[]
    for (market,cohort),methods in sorted(groups.items()):
        base=metric(methods["LEAGUE_PRIOR"])
        team=metric(methods["TEAM_MODEL"]) if "TEAM_MODEL" in methods else metric([])
        out.append({"market":market,"cohort":cohort,"n":base["n"],"league_prior_brier":base["brier"],
                    "league_prior_log_loss":base["log_loss"],"team_brier":team["brier"],"team_log_loss":team["log_loss"],
                    "team_better_both":bool(base["n"]>=min_paired and team["n"]==base["n"] and team["brier"]<base["brier"] and team["log_loss"]<base["log_loss"]),
                    "deployment":"RESEARCH_ONLY"})
    return out

def main():
    p=argparse.ArgumentParser()
    from datetime import datetime
    p.add_argument("--date",default=datetime.now().date().isoformat())
    p.add_argument("--out",default="reports/model-comparison")
    a=p.parse_args()
    leagues=list(dict.fromkeys(re.findall(r'^\|\s*`([^`]+)`\s*\|',get("LEAGUE_INDEX.md"),re.M)))
    rows=[];failed=[]
    for lg in leagues:
        try:rows.extend(evaluate_pair(csvrows("data/"+lg+"/results_2627.csv"),lg,a.date))
        except Exception as exc:failed.append({"league":lg,"error":str(exc)[:120]})
    summary_rows=paired_summary(rows)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with (out/"comparison.csv").open("w",encoding="utf-8-sig",newline="") as f:
        fields=["market","cohort","n","league_prior_brier","league_prior_log_loss","team_brier","team_log_loss","team_better_both","deployment"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(summary_rows)
    summary={"leagues_attempted":len(leagues),"leagues_failed":failed,"predictions":len(rows),"comparisons":summary_rows,
             "warning":"Retrospective, uncalibrated; source may be revised; paired metrics are not forward validation or betting ROI. No deployment."}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"leagues_attempted":len(leagues),"failures":len(failed),"predictions":len(rows),
                      "comparisons":[{"market":r["market"],"cohort":r["cohort"],"n":r["n"],"team_better_both":r["team_better_both"]} for r in summary_rows]},ensure_ascii=False))
    if not leagues or len(failed)==len(leagues):raise SystemExit(2)
if __name__=="__main__":main()
