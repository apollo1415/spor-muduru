#!/usr/bin/env python3
"""Create a human-review queue for provider/source fixture pairs. Never auto-approve."""
import argparse,csv,json
from collections import Counter
from pathlib import Path
from odds_ev import utc_date
from coverage_audit import normalize

FIELDS=["event_id","provider_sport","provider_home","provider_away","provider_kickoff_utc","source_league","source_home","source_away","source_kickoff_istanbul","delta_minutes","team_name_match","source_pairs_for_event","provider_events_for_source","review_status","approved"]
def review(fixtures,events,max_hours=24):
    pairs=[]
    for e in events:
        try:
            et=utc_date(e["commence_time"])
            for f in fixtures:
                if normalize(e["home_team"])!=normalize(f["home"]) or normalize(e["away_team"])!=normalize(f["away"]):continue
                delta=abs((et-utc_date(f["kickoff_istanbul"])).total_seconds())/60
                if delta>max_hours*60:continue
                pairs.append((e,f,delta))
        except (KeyError,TypeError,ValueError):continue
    per_event=Counter(e["id"] for e,f,d in pairs)
    per_fixture=Counter((f["league"],f["home"],f["away"],f["kickoff_istanbul"]) for e,f,d in pairs)
    output=[]
    for e,f,delta in pairs:
        key=(f["league"],f["home"],f["away"],f["kickoff_istanbul"])
        unique=per_event[e["id"]]==1 and per_fixture[key]==1
        output.append({"event_id":e["id"],"provider_sport":e.get("sport_key",""),
                       "provider_home":e["home_team"],"provider_away":e["away_team"],
                       "provider_kickoff_utc":e["commence_time"],"source_league":f["league"],
                       "source_home":f["home"],"source_away":f["away"],
                       "source_kickoff_istanbul":f["kickoff_istanbul"],
                       "delta_minutes":round(delta,2),"team_name_match":"EXACT_NORMALIZED",
                       "source_pairs_for_event":per_event[e["id"]],
                       "provider_events_for_source":per_fixture[key],
                       "review_status":"REVIEW_TIME_AND_LEAGUE" if unique else "AMBIGUOUS_MULTIPLE_PAIRS",
                       "approved":"NO"})
    return sorted(output,key=lambda x:(x["event_id"],x["delta_minutes"]))
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fixtures",default="reports/odds/horizon_fixtures.json")
    p.add_argument("--events",default="reports/odds/provider_events.json")
    p.add_argument("--out",default="reports/odds")
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    fixtures=json.loads(Path(a.fixtures).read_text(encoding="utf-8")) if Path(a.fixtures).exists() else []
    events=json.loads(Path(a.events).read_text(encoding="utf-8")) if Path(a.events).exists() else []
    rows=review(fixtures,events)
    with (out/"fixture_review_queue.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    counts=dict(Counter(r["review_status"] for r in rows))
    summary={"review_rows":len(rows),"counts":counts,"approved":0,
             "warning":"Review queue only. League identity, event date and kickoff must be independently verified before manually adding an approved mapping."}
    (out/"fixture_review_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
