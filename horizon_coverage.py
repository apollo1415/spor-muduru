#!/usr/bin/env python3
"""Compare bookmaker event horizon with 75-league fixture calendar, not only today's matches."""
import argparse,csv,json,re
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path
from spor_muduru import get,csvrows,IST
from odds_ev import utc_date
from coverage_audit import normalize

def compare(fixtures,events):
    rows=[];counts=Counter()
    for e in events:
        try:
            kickoff=utc_date(e["commence_time"])
            same=[f for f in fixtures if normalize(f["home"])==normalize(e["home_team"]) and normalize(f["away"])==normalize(e["away_team"])]
            close=[f for f in same if abs((kickoff-utc_date(f["kickoff_istanbul"])).total_seconds())<=86400]
            if close:status="SAME_TEAMS_WITHIN_24H"
            elif same:status="SAME_TEAMS_OTHER_DATE"
            else:status="NO_EXACT_TEAM_PAIR_IN_HORIZON"
            counts[status]+=1
            best=min(close or same,key=lambda f:abs((kickoff-utc_date(f["kickoff_istanbul"])).total_seconds())) if same else None
            rows.append({"event_id":e["id"],"provider_home":e["home_team"],"provider_away":e["away_team"],
                         "provider_kickoff_utc":e["commence_time"],"source_league":best["league"] if best else "",
                         "source_kickoff":best["kickoff_istanbul"] if best else "",
                         "delta_minutes":round(abs((kickoff-utc_date(best["kickoff_istanbul"])).total_seconds())/60,1) if best else "",
                         "status":status,"approved":"NO"})
        except (KeyError,ValueError,TypeError):counts["INVALID_PROVIDER_EVENT"]+=1
    return rows,dict(sorted(counts.items()))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--events",default="reports/odds/provider_events.json")
    p.add_argument("--out",default="reports/odds")
    p.add_argument("--days",type=int,default=14)
    a=p.parse_args()
    if not 1<=a.days<=30:raise SystemExit("days must be 1..30")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    events=json.loads(Path(a.events).read_text(encoding="utf-8")) if Path(a.events).exists() else []
    valid_times=[]
    for e in events:
        try:valid_times.append(utc_date(e["commence_time"]))
        except (KeyError,ValueError,TypeError):pass
    now=datetime.now(timezone.utc)
    start=now-timedelta(days=1);end=now+timedelta(days=a.days)
    leagues=list(dict.fromkeys(re.findall(r'^\|\s*`([^`]+)`\s*\|',get("LEAGUE_INDEX.md"),re.M)))
    fixtures=[];failures=[]
    for league in leagues:
        try:
            for f in csvrows("data/"+league+"/fixtures_2627.csv"):
                try:
                    dt=datetime.strptime(f["date"]+" "+f["time"],"%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=1)))
                    if start<=dt<=end and f.get("home") and f.get("away"):
                        fixtures.append({"league":league,"home":f["home"],"away":f["away"],
                                         "kickoff_istanbul":dt.astimezone(IST).isoformat()})
                except (ValueError,KeyError,TypeError):pass
        except Exception:failures.append(league)
    (out/"horizon_fixtures.json").write_text(json.dumps(fixtures,ensure_ascii=False),encoding="utf-8")
    rows,counts=compare(fixtures,events)
    fields=["event_id","provider_home","provider_away","provider_kickoff_utc","source_league","source_kickoff","delta_minutes","status","approved"]
    with (out/"horizon_coverage.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={"provider_events":len(events),"source_fixtures_in_horizon":len(fixtures),"days_ahead":a.days,
             "leagues_attempted":len(leagues),"leagues_failed":len(failures),"counts":counts,
             "warning":"Fixture coverage only. No model probabilities or automatic event approval."}
    (out/"horizon_coverage_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
