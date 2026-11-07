#!/usr/bin/env python3
"""Research-only league-prior fallback for fixtures lacking sufficient team history."""
import argparse,csv,json,math
from collections import Counter
from pathlib import Path
from spor_muduru import value,poisson,IST
from datetime import datetime,timezone

def prior(history,cutoff,min_games=20):
    valid=[]
    for r in history:
        if r.get("date","")>=cutoff:continue
        h=value(r.get("ft_home"));a=value(r.get("ft_away"))
        if h is None or a is None or h<0 or a<0:continue
        valid.append((h,a))
    if len(valid)<min_games:return None
    return (sum(h for h,a in valid)/len(valid),sum(a for h,a in valid)/len(valid),len(valid))

def fallback(models,histories,now):
    cutoff=now.astimezone(IST).date().isoformat()
    priors={lg:prior(hist,cutoff) for lg,hist in histories.items()}
    rows=[]
    for m in models:
        if m.get("decision")!="INSUFFICIENT_HISTORY":continue
        lg=m.get("league","");p=priors.get(lg)
        result={"league":lg,"home":m.get("home",""),"away":m.get("away",""),
                "kickoff_istanbul":m.get("kickoff_istanbul",""),"baseline_status":"LEAGUE_PRIOR_RESEARCH_ONLY" if p else "INSUFFICIENT_LEAGUE_HISTORY",
                "eligible_for_odds":"NO","reason":"UNCALIBRATED_FALLBACK_NOT_APPROVED"}
        if p:
            result.update(lambda_home=round(p[0],3),lambda_away=round(p[1],3),league_sample=p[2])
            result.update(poisson(max(.15,min(5,p[0])),max(.15,min(5,p[1]))))
        rows.append(result)
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--models",default="reports/horizon/matches.csv")
    p.add_argument("--out",default="reports/horizon")
    a=p.parse_args()
    with open(a.models,encoding="utf-8-sig",newline="") as f:models=list(csv.DictReader(f))
    from spor_muduru import csvrows
    leagues={m["league"] for m in models if m.get("decision")=="INSUFFICIENT_HISTORY"}
    histories={};failed=[]
    for lg in sorted(leagues):
        try:histories[lg]=csvrows("data/"+lg+"/results_2627.csv")
        except Exception:failed.append(lg)
    rows=fallback(models,histories,datetime.now(timezone.utc))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    fields=["league","home","away","kickoff_istanbul","baseline_status","eligible_for_odds","reason","lambda_home","lambda_away","league_sample","p_home","p_draw","p_away","p_over25","p_btts"]
    with (out/"league_prior_fallback.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
    summary={"insufficient_team_history":len(rows),"league_prior_available":sum(r["baseline_status"]=="LEAGUE_PRIOR_RESEARCH_ONLY" for r in rows),
             "league_history_failed":failed,"odds_eligible":0,
             "warning":"League prior ignores team strength, is uncalibrated and must not be used for betting EV or recommendations."}
    (out/"league_prior_fallback_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
