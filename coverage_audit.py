#!/usr/bin/env python3
"""Audit fixture coverage across provider and model source; no automatic approval."""
import argparse,csv,json,re,unicodedata
from collections import Counter
from pathlib import Path
from odds_ev import utc_date

def normalize(s):
    s=unicodedata.normalize("NFKD",s.casefold())
    s="".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+",s))

def audit(matches,events):
    valid=[]
    for m in matches:
        try:
            if not all(m.get(k) for k in ("home","away","kickoff_istanbul","league")):continue
            valid.append((m,utc_date(m["kickoff_istanbul"])))
        except (TypeError,ValueError,KeyError):continue
    rows=[];counts=Counter()
    for e in events:
        try:
            et=utc_date(e["commence_time"])
            home=normalize(e["home_team"]);away=normalize(e["away_team"])
            same_teams=[(m,t) for m,t in valid if normalize(m["home"])==home and normalize(m["away"])==away]
            exact=[(m,t) for m,t in same_teams if abs((et-t).total_seconds())<=60]
            near=[(m,t) for m,t in same_teams if abs((et-t).total_seconds())<=86400]
            if exact:status="EXACT_TEAMS_AND_TIME_REVIEW"
            elif near:status="SAME_TEAMS_TIME_MISMATCH"
            elif same_teams:status="SAME_TEAMS_DIFFERENT_DATE"
            else:status="NO_EXACT_TEAM_PAIR"
            counts[status]+=1
            m,t=min(exact or near or same_teams,key=lambda x:abs((et-x[1]).total_seconds())) if same_teams else (None,None)
            rows.append({"event_id":e.get("id",""),"provider_home":e["home_team"],"provider_away":e["away_team"],
                         "provider_kickoff_utc":e["commence_time"],"matched_league":m["league"] if m else "",
                         "matched_kickoff":m["kickoff_istanbul"] if m else "",
                         "model_decision":m.get("decision","") if m else "",
                         "delta_minutes":round(abs((et-t).total_seconds())/60,1) if t else "",
                         "status":status,"approved":"NO"})
        except (KeyError,ValueError,TypeError):counts["INVALID_EVENT"]+=1
    return rows,dict(sorted(counts.items()))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matches",default="reports/today/matches.csv")
    p.add_argument("--events",default="reports/odds/provider_events.json")
    p.add_argument("--out",default="reports/odds")
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with open(a.matches,encoding="utf-8-sig",newline="") as f:matches=list(csv.DictReader(f))
    events=json.loads(Path(a.events).read_text(encoding="utf-8")) if Path(a.events).exists() else []
    rows,counts=audit(matches,events)
    fields=["event_id","provider_home","provider_away","provider_kickoff_utc","matched_league","matched_kickoff","model_decision","delta_minutes","status","approved"]
    with (out/"coverage_audit.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={"provider_events":len(events),"source_fixtures":len(matches),"counts":counts,
             "warning":"Exact normalized names do not prove same league or event; no automatic approval. Source covers only selected daily fixtures."}
    (out/"coverage_audit_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
