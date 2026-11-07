#!/usr/bin/env python3
"""Diagnostic coverage audit for provider fixtures; never auto-approves joins."""
import argparse,csv,json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from odds_ev import utc_date
from odds_discovery import score

def diagnose(matches,events):
    eligible=[]
    for m in matches:
        if m.get("decision")!="MODEL_ONLY_NO_ODDS":continue
        try:utc_date(m["kickoff_istanbul"]);eligible.append(m)
        except (KeyError,ValueError,TypeError):continue
    counters=Counter();rows=[]
    for e in events:
        try:
            t=utc_date(e["commence_time"])
            if not eligible:
                counters["no_eligible_modelled_matches"]+=1;continue
            ranked=[]
            for m in eligible:
                delta=abs((t-utc_date(m["kickoff_istanbul"])).total_seconds())/60
                h=score(e["home_team"],m["home"]);a=score(e["away_team"],m["away"])
                ranked.append((delta,-min(h,a),m,h,a))
            same_day=[r for r in ranked if r[0]<=1440]
            near=[r for r in same_day if r[0]<=30]
            if not same_day:reason="NO_MATCH_WITHIN_24H"
            elif not near:reason="KICKOFF_MISMATCH_OVER_30M"
            elif not any(r[3]>=.65 and r[4]>=.65 for r in near):reason="TEAM_NAME_MISMATCH"
            else:reason="CANDIDATE_AVAILABLE"
            counters[reason]+=1
            pool=near or same_day or ranked
            best=min(pool,key=lambda r:(r[0],r[1]))
            m=best[2]
            rows.append({"event_id":e["id"],"provider_home":e["home_team"],"provider_away":e["away_team"],
                         "provider_kickoff_utc":e["commence_time"],"nearest_league":m["league"],
                         "nearest_home":m["home"],"nearest_away":m["away"],
                         "nearest_kickoff_istanbul":m["kickoff_istanbul"],
                         "delta_minutes":round(best[0],1),"home_similarity":round(best[3],3),
                         "away_similarity":round(best[4],3),"reason":reason,
                         "status":"DIAGNOSTIC_ONLY_NOT_APPROVED"})
        except (KeyError,ValueError,TypeError):counters["INVALID_PROVIDER_EVENT"]+=1
    return rows,dict(sorted(counters.items()))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matches",default="reports/today/matches.csv")
    p.add_argument("--events",default="reports/odds/provider_events.json")
    p.add_argument("--out",default="reports/odds")
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with open(a.matches,encoding="utf-8-sig",newline="") as f:matches=list(csv.DictReader(f))
    events=json.loads(Path(a.events).read_text(encoding="utf-8")) if Path(a.events).exists() else []
    rows,counts=diagnose(matches,events)
    fields=["event_id","provider_home","provider_away","provider_kickoff_utc","nearest_league","nearest_home",
            "nearest_away","nearest_kickoff_istanbul","delta_minutes","home_similarity","away_similarity","reason","status"]
    with (out/"matching_diagnostics.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={"provider_events":len(events),"diagnosed":len(rows),"reasons":counts,
             "warning":"Nearest match is NOT a verified match. Never use diagnostics for EV or automatic approval."}
    (out/"matching_diagnostics_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
